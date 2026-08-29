import json
from typing import Any, Optional

from app.core.ai import ai_json


class CandidatureAiError(Exception):
    """Raised when Gemini cannot write the requested deliverables."""


def cv_for_ai(cv: dict[str, Any]) -> dict[str, Any]:
    identity = dict(cv.get("identity") or {})
    identity.pop("photo", None)
    return {
        "title": cv.get("title") or "",
        "identity": {
            "firstName": identity.get("firstName") or "",
            "lastName": identity.get("lastName") or "",
            "title": identity.get("title") or "",
            "email": identity.get("email") or "",
            "phone": identity.get("phone") or "",
            "location": identity.get("location") or "",
            "website": identity.get("website") or "",
            "github": identity.get("github") or "",
        },
        "summary": cv.get("summary") or "",
        "experiences": cv.get("experiences") or [],
        "education": cv.get("education") or [],
        "skills": [
            {"id": item.get("id"), "name": item.get("name"), "level": item.get("level")}
            for item in (cv.get("skills") or [])
            if isinstance(item, dict)
        ],
        "languages": cv.get("languages") or [],
        "projects": cv.get("projects") or [],
        "certifications": cv.get("certifications") or [],
        "interests": [
            {"id": item.get("id"), "name": item.get("name")}
            for item in (cv.get("interests") or [])
            if isinstance(item, dict)
        ],
        "references": cv.get("references") or [],
    }


def valid_checklist(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    items = value.get("items")
    return isinstance(items, list) and len(items) >= 3


def valid_letter(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    return len(str(value.get("body") or "").strip()) >= 160


def valid_cv(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    return len(str(value.get("summary") or "").strip()) >= 40


def merge_adapted_cv(original: dict[str, Any], adapted: dict[str, Any]) -> dict[str, Any]:
    result = json.loads(json.dumps(original))
    if isinstance(adapted.get("title"), str) and adapted["title"].strip():
        result["title"] = adapted["title"].strip()[:120]
    if isinstance(adapted.get("summary"), str) and adapted["summary"].strip():
        result["summary"] = adapted["summary"].strip()[:1800]

    identity = dict(result.get("identity") or {})
    incoming = adapted.get("identity") if isinstance(adapted.get("identity"), dict) else {}
    if isinstance(incoming.get("title"), str) and incoming["title"].strip():
        identity["title"] = incoming["title"].strip()[:80]
    for key in ("firstName", "lastName", "email", "phone", "location", "photo", "website", "github"):
        if (original.get("identity") or {}).get(key):
            identity[key] = (original.get("identity") or {}).get(key)
    result["identity"] = identity
    result["templateId"] = original.get("templateId") or adapted.get("templateId") or "atlas"
    result["principal"] = False

    def merge_list(key: str, text_keys: tuple[str, ...]) -> None:
        source = [item for item in (original.get(key) or []) if isinstance(item, dict)]
        incoming_items = [item for item in (adapted.get(key) or []) if isinstance(item, dict)]
        by_id = {str(item.get("id") or ""): item for item in incoming_items if item.get("id")}
        merged = []
        for index, item in enumerate(source):
            match = by_id.get(str(item.get("id") or ""))
            if match is None and index < len(incoming_items):
                match = incoming_items[index]
            next_item = dict(item)
            if match:
                for field in text_keys:
                    value = match.get(field)
                    if isinstance(value, str) and value.strip():
                        next_item[field] = value
                if isinstance(match.get("bullets"), list):
                    bullets = [str(bullet).strip() for bullet in match["bullets"] if str(bullet).strip()]
                    if bullets:
                        next_item["bullets"] = bullets
            merged.append(next_item)
        result[key] = merged

    merge_list("experiences", ("title", "company", "location", "start", "end"))
    merge_list("education", ("diploma", "school", "year", "details"))
    merge_list("skills", ("name",))
    merge_list("languages", ("name", "level"))
    merge_list("projects", ("name", "description"))
    merge_list("certifications", ("name", "issuer", "year"))
    merge_list("interests", ("name",))
    merge_list("references", ("name", "role", "company"))

    incoming_skills = [item for item in (adapted.get("skills") or []) if isinstance(item, dict)]
    if incoming_skills:
        existing = {str(item.get("name") or "").strip().lower() for item in result.get("skills") or []}
        extra = []
        for item in incoming_skills:
            name = str(item.get("name") or "").strip()
            if not name or name.lower() in existing:
                continue
            extra.append(
                {
                    "id": item.get("id") or f"sk-offer-{len(extra)+1}",
                    "name": name[:80],
                    "level": item.get("level") if isinstance(item.get("level"), int) else 68,
                }
            )
            existing.add(name.lower())
            if len(extra) >= 4:
                break
        if extra:
            result["skills"] = (result.get("skills") or []) + extra

    return result


async def gemini_write_deliverables(
    *,
    offer: str,
    cv: dict[str, Any],
    outputs: list[str],
) -> Optional[dict[str, Any]]:
    snapshot = json.dumps(cv_for_ai(cv), ensure_ascii=False)
    wanted = ", ".join(outputs)
    prompt = f"""Tu rédiges les livrables d'une candidature Nogalix. Tu es un rédacteur RH, pas un extracteur de mots-clés.

Livrables demandés uniquement : {wanted}
Réponds UNIQUEMENT en JSON valide, avec seulement les clés demandées.

Schéma possible :
{{
  "checklist": {{
    "job_title": "",
    "company": null,
    "keywords_found": [],
    "keywords_missing": [],
    "items": [{{"id":"","label":"","ok":true,"detail":""}}],
    "summary": ""
  }},
  "letter": {{"title":"","body":""}},
  "cv": {{
    "title": "",
    "identity": {{"firstName":"","lastName":"","title":"","email":"","phone":"","location":""}},
    "summary": "",
    "experiences": [{{"id":"","title":"","company":"","location":"","start":"","end":"","current":false,"bullets":[]}}],
    "education": [{{"id":"","diploma":"","school":"","year":"","details":""}}],
    "skills": [{{"id":"","name":"","level":70}}],
    "languages": [{{"id":"","name":"","level":""}}],
    "projects": [{{"id":"","name":"","description":""}}],
    "certifications": [{{"id":"","name":"","issuer":"","year":""}}],
    "interests": [{{"id":"","name":""}}],
    "references": [{{"id":"","name":"","role":"","company":"","phone":"","email":""}}]
  }}
}}

Règles de rédaction :
- Français professionnel, fluide, cohérent d'un bout à l'autre. Pas de tiret comme ponctuation.
- N'invente aucune expérience, diplôme, entreprise, date ou compétence absente du CV. Tu reformules, tu réordonnes, tu cibles.
- checklist : 5 à 7 actions concrètes, liées à CETTE offre. summary en 2 phrases. keywords_found / keywords_missing = vrais termes de l'annonce.
- letter : lettre complète (180 à 280 mots), personnalisée (poste, entreprise, 2 preuves du CV). Tutoiement interdit. Signature avec le nom du CV.
- cv : variante prête à envoyer. Accroche réécrite pour le poste. Titre de poste aligné. Missions reformulées avec le vocabulaire de l'offre, sans mentir. Conserve STRICTEMENT les mêmes ids et le même nombre d'expériences / formations.
- Si un livrable n'est pas demandé, omets sa clé.

Offre d'emploi :
{offer[:10000]}

CV source :
{snapshot}
"""

    return await ai_json(prompt, purpose="candidature")


async def write_deliverables(
    *,
    offer: str,
    cv: dict[str, Any],
    outputs: list[str],
    local_checklist,
    job_title: str,
) -> dict[str, Any]:
    needs_writing = any(item in outputs for item in ("cv", "letter"))
    gemini = await gemini_write_deliverables(offer=offer, cv=cv, outputs=outputs)

    if needs_writing and not gemini:
        raise CandidatureAiError(
            "L'IA n'a pas pu rédiger les livrables. Réessayez dans un instant."
        )

    result: dict[str, Any] = {
        "source": "gemini" if gemini else "local",
        "offer_title": job_title,
    }

    if "checklist" in outputs:
        checklist = (gemini or {}).get("checklist") if gemini else None
        result["checklist"] = checklist if valid_checklist(checklist) else local_checklist()
        if gemini and not valid_checklist(checklist) and not needs_writing:
            result["source"] = "local"

    if "letter" in outputs:
        letter = (gemini or {}).get("letter") if gemini else None
        if not valid_letter(letter):
            raise CandidatureAiError(
                "L'IA n'a pas pu rédiger la lettre de motivation. Réessayez."
            )
        result["letter"] = {
            "title": str(letter.get("title") or f"Lettre · {job_title}").strip()[:120],
            "body": str(letter.get("body") or "").strip(),
        }

    if "cv" in outputs:
        adapted = (gemini or {}).get("cv") if gemini else None
        if not valid_cv(adapted):
            raise CandidatureAiError("L'IA n'a pas pu rédiger le CV adapté. Réessayez.")
        result["cv"] = merge_adapted_cv(cv, adapted)

    if gemini and ("letter" in outputs or "cv" in outputs):
        result["source"] = "gemini"

    return result
