import json
import re
import secrets
from typing import Any, Optional

import httpx

from app.core.config import settings
from app.modules.cv.import_parse import finalize_import_payload, parse_imported_cv
from app.modules.cv.match_analyse import _extract_job_title, _parse_json_object

IMPORT_ORIGINAL_TEMPLATE_ID = "import-original"


def _new_id(prefix: str) -> str:
    return f"{prefix}-{secrets.token_hex(4)}"


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


def _cv_corpus(cv: dict[str, Any]) -> str:
    identity = cv.get("identity") or {}
    parts = [
        str(identity.get("title") or ""),
        str(cv.get("summary") or ""),
        " ".join(str(skill.get("name") or "") for skill in cv.get("skills") or []),
    ]
    for exp in cv.get("experiences") or []:
        parts.append(str(exp.get("title") or ""))
        parts.extend(str(bullet) for bullet in exp.get("bullets") or [])
    return " ".join(part for part in parts if part).lower()


def _minimal_cv_from_text(text: str, file_name: str) -> dict[str, Any]:
    from app.modules.cv.import_parse import local_parse_imported_cv

    return local_parse_imported_cv(text, file_name)


def _apply_rewrite_actions(cv: dict[str, Any], actions: list[dict[str, str]], job_title: str) -> dict[str, Any]:
    result = json.loads(json.dumps(cv))
    identity = dict(result.get("identity") or {})
    if job_title and job_title != "Poste ciblé":
        identity["title"] = job_title[:80]
    result["identity"] = identity

    action_text = " ".join(f"{a.get('title', '')} {a.get('detail', '')}" for a in actions).lower()
    summary = (result.get("summary") or "").strip()
    if actions and summary:
        hints = ". ".join(a.get("detail", "")[:120] for a in actions[:2] if a.get("detail"))
        if hints and hints.lower() not in summary.lower():
            result["summary"] = f"{summary.rstrip('.')}. {hints}"[:1800]

    if "compétence" in action_text or "mots clé" in action_text or "mot clé" in action_text:
        skills = list(result.get("skills") or [])
        existing = {str(s.get("name") or "").lower() for s in skills}
        for word in _tokenize(action_text)[:6]:
            label = word.replace(".", " ").strip().title()
            if len(label) < 4 or label.lower() in existing:
                continue
            skills.append({"id": _new_id("sk"), "name": label, "level": 65})
            existing.add(label.lower())
        result["skills"] = skills[:16]

    return result


def local_rewrite_cv(
    *,
    cv: dict[str, Any],
    job_offer: str,
    template_id: str,
    actions: list[dict[str, str]],
    job_title: Optional[str] = None,
) -> dict[str, Any]:
    title = job_title or _extract_job_title(job_offer)
    tokens = _tokenize(job_offer)
    corpus = _cv_corpus(cv)
    missing = [word for word in tokens if word not in corpus][:8]
    found = [word for word in tokens if word in corpus][:8]

    identity = dict(cv.get("identity") or {})
    if title and title != "Poste ciblé":
        identity["title"] = title[:80]

    base_summary = (cv.get("summary") or "").strip()
    highlight = ", ".join(found[:4] or tokens[:4])
    target = f"Poste visé : {title}."
    if base_summary:
        summary = f"{base_summary.rstrip('.')}. {target} Points forts : {highlight}."
    else:
        summary = f"Profil orienté vers {title}. Points forts : {highlight}."
    if missing:
        summary += f" À renforcer sur le CV : {', '.join(missing[:4])}."
    summary = summary[:1800]

    skills = list(cv.get("skills") or [])
    existing_names = {str(s.get("name") or "").lower() for s in skills}
    for word in missing[:5]:
        label = word.replace(".", " ").strip().title()
        if label.lower() in existing_names:
            continue
        skills.append({"id": _new_id("sk"), "name": label, "level": 65})
        existing_names.add(label.lower())

    experiences = []
    for exp in cv.get("experiences") or []:
        item = dict(exp)
        bullets = list(item.get("bullets") or [])
        if missing and bullets:
            tip = missing[0].replace(".", " ")
            joined = " ".join(bullets).lower()
            if tip.lower() not in joined:
                bullets.append(f"Contribution en lien avec {tip}, alignée sur le poste visé.")
                item["bullets"] = bullets
        experiences.append(item)

    rewritten = {
        "templateId": template_id,
        "title": f"CV · {title}"[:120],
        "principal": False,
        "editorStatus": "draft",
        "identity": identity,
        "summary": summary,
        "experiences": experiences,
        "education": cv.get("education") or [],
        "skills": skills[:16],
        "languages": cv.get("languages") or [],
        "projects": cv.get("projects") or [],
        "certifications": cv.get("certifications") or [],
        "interests": cv.get("interests") or [],
    }
    return _apply_rewrite_actions(rewritten, actions, title)


async def gemini_rewrite_cv(
    *,
    cv: dict[str, Any],
    cv_text: str,
    job_offer: str,
    template_id: str,
    actions: list[dict[str, str]],
    job_title: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    if not settings.gemini_enabled or not settings.gemini_api_key:
        return None

    actions_json = json.dumps(actions, ensure_ascii=False)[:3000]
    source = json.dumps(cv, ensure_ascii=False)[:7000] if cv.get("experiences") or cv.get("skills") else cv_text[:7000]
    title = job_title or _extract_job_title(job_offer)

    prompt = f"""Tu prépares un CV Nogalix pré rempli et corrigé à partir d'un CV source et d'une offre d'emploi.
L'offre sert uniquement de référence. On ne modifie jamais l'offre, seulement le CV.

Objectif :
1) restructurer le contenu du CV source en sections Nogalix ;
2) appliquer les corrections listées ci dessous pour mieux correspondre à l'offre.

Corrections à appliquer sur le CV :
{actions_json}

Réponds UNIQUEMENT en JSON valide :
{{
  "templateId": "{template_id}",
  "title": "",
  "principal": false,
  "editorStatus": "draft",
  "identity": {{"firstName":"","lastName":"","title":"","email":"","phone":"","location":"","photo":null,"website":"","github":""}},
  "summary": "",
  "experiences": [{{"id":"","title":"","company":"","location":"","start":"","end":"","current":false,"bullets":[]}}],
  "education": [{{"id":"","diploma":"","school":"","year":"","details":""}}],
  "skills": [{{"id":"","name":"","level":70}}],
  "languages": [{{"id":"","name":"","level":""}}],
  "projects": [],
  "certifications": [],
  "interests": []
}}

Règles :
Français professionnel, orienté modification du CV uniquement.
Ne jamais utiliser le tiret comme ponctuation dans les textes affichés.
N'invente pas d'expériences ou diplômes absents du CV source.
Tu peux reformuler, réordonner et enrichir les puces avec le vocabulaire de l'offre.
Le titre du CV doit refléter le poste : {title}.

Offre d'emploi :
{job_offer[:8000]}

CV source :
{source}
"""

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent"
    )
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": max(int(settings.gemini_max_output_tokens or 512), 2048),
            "temperature": 0.35,
            "responseMimeType": "application/json",
        },
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                params={"key": settings.gemini_api_key},
                json=body,
            )
        if response.status_code != 200:
            return None
        data = response.json()
        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        texts = [p.get("text", "") for p in parts if p.get("text")]
        parsed = _parse_json_object("\n".join(texts).strip())
        if not parsed:
            return None
        parsed["templateId"] = template_id
        parsed["principal"] = False
        parsed["editorStatus"] = "draft"
        return parsed
    except Exception:
        return None


async def build_rewrite_cv(
    *,
    cv: dict[str, Any],
    cv_text: str,
    job_offer: str,
    template_id: str,
    actions: list[dict[str, str]],
    job_title: Optional[str] = None,
    file_name: str = "",
) -> dict[str, Any]:
    is_import = (template_id or "").strip().lower() == IMPORT_ORIGINAL_TEMPLATE_ID
    needs_parse = not cv.get("experiences") and not cv.get("education") and not cv.get("skills")

    if needs_parse and cv_text:
        parsed = await parse_imported_cv(cv_text, file_name)
        cv = parsed["payload"]
        parse_source = parsed["source"]
    else:
        parse_source = None

    if is_import:
        return {"payload": finalize_import_payload(cv), "source": parse_source or "local"}

    ai = await gemini_rewrite_cv(
        cv=cv,
        cv_text=cv_text,
        job_offer=job_offer,
        template_id=template_id,
        actions=actions,
        job_title=job_title,
    )
    if ai:
        return {"payload": ai, "source": "ai"}
    return {
        "payload": local_rewrite_cv(
            cv=cv,
            job_offer=job_offer,
            template_id=template_id,
            actions=actions,
            job_title=job_title,
        ),
        "source": parse_source or "local",
    }
