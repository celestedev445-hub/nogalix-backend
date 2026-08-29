import json
from typing import Any, Optional

from app.core.ai import ai_json


class CvTranslateError(Exception):
    """Raised when Gemini cannot translate the CV."""


PRESERVED_IDENTITY = ("firstName", "lastName", "email", "phone", "photo", "website", "github")
LIST_KEYS = (
    "experiences",
    "education",
    "skills",
    "languages",
    "projects",
    "certifications",
    "interests",
    "references",
)


def _clean_cv_for_ai(cv: dict[str, Any]) -> dict[str, Any]:
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
            {key: item.get(key) for key in ("id", "name", "level") if key in item or key == "id"}
            for item in (cv.get("skills") or [])
            if isinstance(item, dict)
        ],
        "languages": cv.get("languages") or [],
        "projects": cv.get("projects") or [],
        "certifications": cv.get("certifications") or [],
        "interests": [
            {key: item.get(key) for key in ("id", "name") if key in item or key == "id"}
            for item in (cv.get("interests") or [])
            if isinstance(item, dict)
        ],
        "references": cv.get("references") or [],
    }


def _as_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _merge_item(original: dict[str, Any], translated: dict[str, Any], text_keys: tuple[str, ...]) -> dict[str, Any]:
    merged = dict(original)
    for key in text_keys:
        value = translated.get(key)
        if isinstance(value, str) and value.strip():
            merged[key] = value
    if "bullets" in original or "bullets" in translated:
        original_bullets = original.get("bullets") if isinstance(original.get("bullets"), list) else []
        translated_bullets = translated.get("bullets") if isinstance(translated.get("bullets"), list) else []
        bullets: list[str] = []
        count = max(len(original_bullets), len(translated_bullets))
        for index in range(count):
            raw = translated_bullets[index] if index < len(translated_bullets) else None
            fallback = original_bullets[index] if index < len(original_bullets) else ""
            text = raw.strip() if isinstance(raw, str) and raw.strip() else str(fallback or "")
            if text:
                bullets.append(text)
        merged["bullets"] = bullets
    if "current" in original:
        merged["current"] = bool(original.get("current"))
    if "level" in original and "level" in translated:
        if isinstance(original.get("level"), int):
            merged["level"] = original["level"]
        elif isinstance(translated.get("level"), str) and translated["level"].strip():
            merged["level"] = translated["level"]
    if "icon" in original:
        merged["icon"] = original.get("icon")
    if "url" in original:
        merged["url"] = original.get("url")
    return merged


def _merge_list(
    original: list[dict[str, Any]],
    translated: list[dict[str, Any]],
    text_keys: tuple[str, ...],
) -> list[dict[str, Any]]:
    by_id = {str(item.get("id") or ""): item for item in translated if item.get("id")}
    merged: list[dict[str, Any]] = []
    for index, item in enumerate(original):
        match = by_id.get(str(item.get("id") or ""))
        if match is None and index < len(translated):
            match = translated[index]
        merged.append(_merge_item(item, match or {}, text_keys))
    return merged


def merge_translated_cv(original: dict[str, Any], translated: dict[str, Any]) -> dict[str, Any]:
    result = json.loads(json.dumps(original))
    if isinstance(translated.get("title"), str) and translated["title"].strip():
        result["title"] = translated["title"].strip()[:120]
    if isinstance(translated.get("summary"), str):
        result["summary"] = translated["summary"]

    identity = dict(result.get("identity") or {})
    incoming = translated.get("identity") if isinstance(translated.get("identity"), dict) else {}
    if isinstance(incoming.get("title"), str) and incoming["title"].strip():
        identity["title"] = incoming["title"].strip()[:80]
    if isinstance(incoming.get("location"), str) and incoming["location"].strip():
        identity["location"] = incoming["location"].strip()
    for key in PRESERVED_IDENTITY:
        if key in (original.get("identity") or {}):
            identity[key] = (original.get("identity") or {}).get(key)
    result["identity"] = identity

    result["experiences"] = _merge_list(
        _as_list(original.get("experiences")),
        _as_list(translated.get("experiences")),
        ("title", "company", "location", "start", "end"),
    )
    result["education"] = _merge_list(
        _as_list(original.get("education")),
        _as_list(translated.get("education")),
        ("diploma", "school", "year", "details"),
    )
    result["skills"] = _merge_list(
        _as_list(original.get("skills")),
        _as_list(translated.get("skills")),
        ("name",),
    )
    result["languages"] = _merge_list(
        _as_list(original.get("languages")),
        _as_list(translated.get("languages")),
        ("name", "level"),
    )
    result["projects"] = _merge_list(
        _as_list(original.get("projects")),
        _as_list(translated.get("projects")),
        ("name", "description"),
    )
    result["certifications"] = _merge_list(
        _as_list(original.get("certifications")),
        _as_list(translated.get("certifications")),
        ("name", "issuer", "year"),
    )
    result["interests"] = _merge_list(
        _as_list(original.get("interests")),
        _as_list(translated.get("interests")),
        ("name",),
    )
    result["references"] = _merge_list(
        _as_list(original.get("references")),
        _as_list(translated.get("references")),
        ("name", "role", "company"),
    )
    return result


def _has_translatable_content(cv: dict[str, Any]) -> bool:
    identity = cv.get("identity") or {}
    if str(identity.get("title") or "").strip() or str(identity.get("location") or "").strip():
        return True
    if str(cv.get("summary") or "").strip():
        return True
    return any(cv.get(key) for key in LIST_KEYS)


async def gemini_translate_cv(
    *,
    cv: dict[str, Any],
    language_name: str,
    language_code: str,
) -> Optional[dict[str, Any]]:
    source = json.dumps(_clean_cv_for_ai(cv), ensure_ascii=False)
    prompt = f"""Tu traduis un CV Nogalix vers la langue cible, pour un usage professionnel.

Langue cible : {language_name} (code {language_code})

Réponds UNIQUEMENT en JSON valide, même structure que le CV source :
{{
  "title": "",
  "identity": {{"firstName":"","lastName":"","title":"","email":"","phone":"","location":"","website":"","github":""}},
  "summary": "",
  "experiences": [{{"id":"","title":"","company":"","location":"","start":"","end":"","current":false,"bullets":[]}}],
  "education": [{{"id":"","diploma":"","school":"","year":"","details":""}}],
  "skills": [{{"id":"","name":"","level":70}}],
  "languages": [{{"id":"","name":"","level":""}}],
  "projects": [{{"id":"","name":"","description":"","url":""}}],
  "certifications": [{{"id":"","name":"","issuer":"","year":""}}],
  "interests": [{{"id":"","name":""}}],
  "references": [{{"id":"","name":"","role":"","company":"","phone":"","email":""}}]
}}

Règles de traduction :
- Traduis TOUT le contenu rédactionnel de façon cohérente : même vocabulaire, même registre, mêmes temps, même ton du début à la fin.
- Adapte le style à un CV professionnel en {language_name}, pas un mot-à-mot.
- Conserve STRICTEMENT les mêmes ids et le même nombre d'éléments dans chaque liste. Ne fusionne rien, n'ajoute rien, n'omets rien.
- Ne traduis pas : prénom, nom, e-mail, téléphone, sites, GitHub, URL, noms d'entreprises, noms d'écoles, noms de technologies (React, Python, Excel).
- Traduis : titre de poste, accroche, missions, diplômes, compétences en langage courant, niveaux de langue, lieux, intitulés de projets, certifications, centres d'intérêt, fonctions et entreprises des références, libellés de dates du type Présent / Actuel / Current.
- Ne traduis pas les noms, e-mails et téléphones des références.
- Laisse les années et dates numériques telles quelles.
- N'invente aucune expérience, compétence ou diplôme.
- Pas de tiret utilisé comme ponctuation dans les textes affichés.

CV source :
{source}
"""

    return await ai_json(prompt, purpose="translate")


async def translate_cv(
    *,
    cv: dict[str, Any],
    language_name: str,
    language_code: str,
) -> dict[str, Any]:
    if not _has_translatable_content(cv):
        raise CvTranslateError("Le CV ne contient pas assez de texte à traduire.")

    translated = await gemini_translate_cv(
        cv=cv,
        language_name=language_name,
        language_code=language_code,
    )
    if not translated:
        raise CvTranslateError("L'IA n'a pas pu traduire le CV. Réessayez dans un instant.")

    return {
        "payload": merge_translated_cv(cv, translated),
        "source": "ai",
        "languageName": language_name,
    }
