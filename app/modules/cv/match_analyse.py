import re
from typing import Any, Optional

from app.core.ai import ai_json


def _tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-zàâäéèêëïîôùûüç0-9+#.]{4,}", text.lower())
    seen: set[str] = set()
    tokens: list[str] = []
    for word in words:
        if word in seen:
            continue
        seen.add(word)
        tokens.append(word)
    return tokens


def _extract_job_title(offer: str) -> str:
    lines = [line.strip() for line in offer.splitlines() if line.strip()]
    if not lines:
        return "Poste ciblé"
    first = lines[0][:100]
    if len(first) < 8 and len(lines) > 1:
        return lines[1][:100]
    return first


def _cv_to_text(cv: dict[str, Any]) -> str:
    identity = cv.get("identity") or {}
    parts = [
        str(identity.get("title") or ""),
        str(cv.get("summary") or ""),
        " ".join(str(skill.get("name") or "") for skill in cv.get("skills") or []),
    ]
    for exp in cv.get("experiences") or []:
        parts.append(str(exp.get("title") or ""))
        parts.append(str(exp.get("company") or ""))
        parts.extend(str(bullet) for bullet in exp.get("bullets") or [])
    for edu in cv.get("education") or []:
        parts.append(str(edu.get("diploma") or ""))
        parts.append(str(edu.get("school") or ""))
    return " ".join(part for part in parts if part).strip()


def _verdict_from_score(score: int) -> tuple[str, str]:
    if score >= 75:
        return "forte", "Votre CV correspond bien à l'offre"
    if score >= 50:
        return "partielle", "Correspondance partielle. Modifiez votre CV pour vous rapprocher de l'offre"
    return "faible", "Votre CV ne correspond pas encore à l'offre"


def local_match_analysis(
    *,
    cv_label: str,
    cv_text: str,
    job_offer: str,
    cv_id: Optional[str] = None,
) -> dict[str, Any]:
    offer_tokens = _tokenize(job_offer)
    cv_tokens = set(_tokenize(cv_text))
    if not offer_tokens:
        offer_tokens = _tokenize(job_offer[:500])

    aligned = [word for word in offer_tokens if word in cv_tokens][:6]
    missing = [word for word in offer_tokens if word not in cv_tokens][:6]
    ratio = len(aligned) / max(len(offer_tokens[:12]), 1)
    base = 35 + int(ratio * 55)
    if len(cv_text) > 400:
        base += 5
    if len(aligned) >= 4:
        base += 5
    match_score = max(20, min(92, base))
    verdict, verdict_label = _verdict_from_score(match_score)
    job_title = _extract_job_title(job_offer)

    aligned_points = []
    if aligned:
        aligned_points.append(
            f"Compétences ou termes de l'offre déjà visibles dans votre CV : {', '.join(aligned[:4])}."
        )
    if cv_text and job_title.lower() in cv_text.lower():
        aligned_points.append(f"Votre titre ou profil mentionne déjà « {job_title[:60]} ».")

    gaps = []
    if missing:
        gaps.append(
            f"L'offre attend ces éléments, absents ou peu visibles dans votre CV : {', '.join(missing[:4])}."
        )
    if match_score < 75:
        gaps.append(
            "Votre accroche et vos expériences ne reprennent pas assez le vocabulaire exact de l'annonce."
        )

    actions = []
    if missing:
        actions.append(
            {
                "title": "Accroche et expériences : reprendre les mots clés",
                "detail": (
                    f"Dans votre résumé et vos 2 dernières expériences, ajoutez ou reformulez pour "
                    f"intégrer : {', '.join(missing[:3])}."
                ),
            }
        )
    if match_score < 60:
        actions.append(
            {
                "title": "Titre du CV : l'aligner sur le poste",
                "detail": (
                    f"Modifiez votre titre actuel pour qu'il corresponde à « {job_title[:60]} »."
                ),
            }
        )
    else:
        actions.append(
            {
                "title": "Compétences : mettre en avant celles de l'offre",
                "detail": (
                    "Réorganisez votre section compétences sur le CV : placez en premier celles "
                    "citées dans l'annonce."
                ),
            }
        )
    actions.append(
        {
            "title": "Expériences : reformuler les missions",
            "detail": (
                "Reformulez 1 à 2 puces par expérience sur votre CV en reprenant les verbes et "
                "attentes de l'offre, avec des résultats chiffrés si possible."
            ),
        }
    )

    if verdict == "forte":
        summary = (
            f"Votre CV est globalement aligné avec « {job_title} ». "
            "Quelques retouches sur votre CV peuvent encore renforcer votre candidature."
        )
    elif verdict == "partielle":
        summary = (
            f"Votre CV couvre une partie de « {job_title} ». "
            "Modifiez votre CV pour rendre plus visibles les éléments attendus par l'offre."
        )
    else:
        summary = (
            f"Votre CV n'est pas encore adapté à « {job_title} ». "
            "Modifiez votre CV avec les conseils listés ci dessous avant de candidater."
        )

    return {
        "matchScore": match_score,
        "verdict": verdict,
        "verdictLabel": verdict_label,
        "summary": summary,
        "alignedPoints": aligned_points[:4],
        "gaps": gaps[:4],
        "actions": actions[:4],
        "source": "local",
        "cvLabel": cv_label,
        "jobTitle": job_title,
        "cvId": cv_id,
    }


async def gemini_match_analysis(
    *,
    cv_label: str,
    cv_text: str,
    job_offer: str,
    cv_id: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    prompt = f"""Tu es une experte recrutement et ATS pour Nogalix.
L'utilisateur veut savoir :
1) si son CV correspond à cette offre d'emploi (l'offre sert uniquement de référence, on ne la modifie jamais) ;
2) quelles modifications concrètes faire SUR SON CV pour mieux correspondre à l'offre.

Réponds UNIQUEMENT en JSON valide (pas de markdown) :
{{
  "matchScore": 0,
  "verdict": "forte|partielle|faible",
  "verdictLabel": "Votre CV correspond bien à l'offre|Correspondance partielle. Modifiez votre CV pour vous rapprocher de l'offre|Votre CV ne correspond pas encore à l'offre",
  "summary": "1 à 2 phrases : le CV correspond il à l'offre, et quoi modifier sur le CV",
  "alignedPoints": ["ce qui est déjà aligné entre le CV et l'offre"],
  "gaps": ["ce que l'offre demande mais qui manque ou ressort peu dans le CV"],
  "actions": [{{"title": "section du CV à modifier (ex: Titre, Accroche, Compétences, Expériences)", "detail": "modification précise à faire sur le CV, formulée à la 2e personne"}}],
  "jobTitle": "intitulé du poste détecté"
}}

Règles :
Français professionnel, direct, orienté modification du CV uniquement.
Maximum 4 alignedPoints, 4 gaps, 4 actions.
Les actions sont des modifications concrètes à faire sur le CV, jamais sur l'offre.
Chaque action indique quelle partie du CV modifier et quoi y mettre ou reformuler.
Ne jamais utiliser le tiret comme ponctuation dans les textes affichés à l'utilisateur.
matchScore entre 0 et 100 (cohérent avec verdict).
verdict "forte" si >= 75, "partielle" si 50 à 74, "faible" si < 50.
Ne mentionne que ce qui est pertinent pour CETTE offre et CE CV.
N'invente pas de compétences ou expériences absentes du CV.

Offre d'emploi :
{job_offer[:9000]}

CV ({cv_label}) :
{cv_text[:9000]}
"""

    try:
        parsed = await ai_json(prompt, purpose="match")
        if not parsed:
            return None

        score = int(parsed.get("matchScore") or 0)
        score = max(0, min(100, score))
        verdict = parsed.get("verdict") or _verdict_from_score(score)[0]
        if verdict not in {"forte", "partielle", "faible"}:
            verdict, verdict_label = _verdict_from_score(score)
        else:
            verdict_label = str(parsed.get("verdictLabel") or _verdict_from_score(score)[1])

        actions = []
        for item in parsed.get("actions") or []:
            if isinstance(item, dict) and item.get("title"):
                actions.append(
                    {
                        "title": str(item.get("title") or "")[:120],
                        "detail": str(item.get("detail") or "")[:240],
                    }
                )

        return {
            "matchScore": score,
            "verdict": verdict,
            "verdictLabel": verdict_label[:80],
            "summary": str(parsed.get("summary") or "")[:500],
            "alignedPoints": [str(x)[:160] for x in (parsed.get("alignedPoints") or [])[:4]],
            "gaps": [str(x)[:160] for x in (parsed.get("gaps") or [])[:4]],
            "actions": actions[:4],
            "source": "ai",
            "cvLabel": cv_label,
            "jobTitle": str(parsed.get("jobTitle") or _extract_job_title(job_offer))[:120],
            "cvId": cv_id,
        }
    except Exception:
        return None


async def build_match_analysis(
    *,
    cv_label: str,
    cv_text: str,
    job_offer: str,
    cv_id: Optional[str] = None,
) -> dict[str, Any]:
    ai = await gemini_match_analysis(
        cv_label=cv_label,
        cv_text=cv_text,
        job_offer=job_offer,
        cv_id=cv_id,
    )
    if ai:
        return ai
    return local_match_analysis(
        cv_label=cv_label,
        cv_text=cv_text,
        job_offer=job_offer,
        cv_id=cv_id,
    )
