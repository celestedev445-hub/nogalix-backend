import json
import re
import secrets
from typing import Any, Optional

import httpx

from app.core.config import settings
from app.modules.cv.match_analyse import _parse_json_object


def _new_id(prefix: str) -> str:
    return f"{prefix}-{secrets.token_hex(4)}"


SECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("summary", re.compile(r"^(profil|résumé|resume|summary|à propos|a propos|accroche|objectif)\b", re.I)),
    (
        "experience",
        re.compile(
            r"^(expériences?(?:\s+professionnelles?)?|experiences?(?:\s+professional)?|parcours(?:\s+professionnel)?|emplois?|professional(?:\s+experience)?|work\s+experience)\b",
            re.I,
        ),
    ),
    (
        "education",
        re.compile(
            r"^(formations?(?:\s+académiques?)?|éducation|education|diplômes?|diplomes?|études|etudes|scolarité|scolarite)\b",
            re.I,
        ),
    ),
    ("skills", re.compile(r"^(compétences?(?:\s+techniques?)?|competences?(?:\s+techniques?)?|skills?|expertises?|outils?|savoirs?)\b", re.I)),
    ("languages", re.compile(r"^(langues?|languages?|idiomes?)\b", re.I)),
    ("projects", re.compile(r"^(projets?(?:\s+personnels?)?|projects?|portfolio|réalisations?|realisations?)\b", re.I)),
    ("certifications", re.compile(r"^(certifications?|certificats?|licences?|attestations?)\b", re.I)),
    ("interests", re.compile(r"^(centres?\s+d.intérêt|intérêts?|interets?|loisirs?|hobbys?|passions?)\b", re.I)),
]

DATE_RANGE = re.compile(
    r"(?P<start>(?:\d{1,2}[/.-])?(?:19|20)\d{2})\s*(?:[-–—àa]|to|au)\s*(?P<end>(?:\d{1,2}[/.-])?(?:19|20)\d{2}|présent|present|aujourd'hui|actuel|current)",
    re.I,
)
YEAR_ONLY = re.compile(r"\b(19|20)\d{2}\b")
EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.\w+")
PHONE = re.compile(r"(?:\+?\d[\d\s().-]{8,}\d)")
BULLET = re.compile(r"^[\-•*▪▫◦]\s*")
JOB_TITLE_HINTS = re.compile(
    r"\b("
    r"développeur|developpeur|ingénieur|ingenieur|engineer|developer|designer|architecte|architect|"
    r"chef|manager|consultant|analyste|analyst|technicien|technician|commercial|comptable|"
    r"avocat|médecin|medecin|infirmier|professeur|formateur|stagiaire|alternant|intern|"
    r"responsable|directeur|director|freelance|product|marketing|data|devops|"
    r"full[\s-]?stack|front[\s-]?end|back[\s-]?end|fullstack|frontend|backend|"
    r"rh|sales|support|administrateur|administrator|lead|head|senior|junior"
    r")\b",
    re.I,
)


def _detect_section(line: str) -> Optional[str]:
    stripped = line.strip().rstrip(":-–—.")
    if not stripped or len(stripped) > 80:
        return None
    for section, pattern in SECTION_PATTERNS:
        if pattern.match(stripped):
            return section
    compact = re.sub(r"[^\w\sàâäéèêëïîôùûüç'-]", "", stripped, flags=re.I)
    if compact and len(compact) <= 40 and compact == compact.upper() and any(ch.isalpha() for ch in compact):
        lowered = compact.lower()
        for section, pattern in SECTION_PATTERNS:
            if pattern.match(lowered):
                return section
    return None


def _looks_like_contact(line: str) -> bool:
    lower = line.lower()
    return bool(
        EMAIL.search(line)
        or PHONE.search(line)
        or "linkedin" in lower
        or "github" in lower
        or "http://" in lower
        or "https://" in lower
        or "www." in lower
    )


def _parse_contact_fields(text: str, header_lines: list[str]) -> dict[str, str]:
    blob = "\n".join(header_lines) + "\n" + text
    email = (EMAIL.search(blob).group(0) if EMAIL.search(blob) else "") or ""
    phone = _extract_phones(blob)
    website = ""
    github = ""
    location = ""

    for line in header_lines:
        lower = line.lower()
        if "github.com" in lower:
            github = line.strip()
        elif "linkedin.com" in lower or lower.startswith("www.") or lower.startswith("http"):
            website = line.strip()
        elif not EMAIL.search(line) and not PHONE.search(line) and len(line) < 70:
            if any(marker in lower for marker in ("paris", "france", "cameroun", "douala", "yaoundé", "yaounde", "abidjan")):
                location = line.strip()

    return {
        "email": email,
        "phone": phone,
        "location": location,
        "website": website,
        "github": github,
    }


def _split_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {
        "header": [],
        "summary": [],
        "experience": [],
        "education": [],
        "skills": [],
        "languages": [],
        "projects": [],
        "certifications": [],
        "interests": [],
    }
    current = "header"
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        detected = _detect_section(line)
        if detected:
            current = detected
            continue
        sections[current].append(line)
    return sections


def _looks_like_job_title(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if JOB_TITLE_HINTS.search(stripped):
        return True
    if "/" in stripped and len(stripped) < 90:
        return True
    if " - " in stripped and JOB_TITLE_HINTS.search(stripped.split(" - ", 1)[0]):
        return True
    return False


def _looks_like_person_name(line: str) -> bool:
    stripped = line.strip()
    if not stripped or EMAIL.search(stripped) or PHONE.search(stripped):
        return False
    if DATE_RANGE.search(stripped) or _detect_section(stripped):
        return False
    if _looks_like_job_title(stripped):
        return False
    if len(stripped) > 50 or len(stripped) < 2:
        return False
    words = [word for word in re.split(r"\s+", stripped) if word]
    if not 1 <= len(words) <= 4:
        return False
    if any(ch.isdigit() for ch in stripped):
        return False
    return True


def _extract_phones(text: str) -> str:
    seen: set[str] = set()
    phones: list[str] = []
    for match in PHONE.finditer(text):
        raw = re.sub(r"\s+", " ", match.group(0).strip())
        digits = re.sub(r"\D", "", raw)
        if len(digits) < 8 or digits in seen:
            continue
        seen.add(digits)
        phones.append(raw)
    return " | ".join(phones[:4])


def _split_person_name(line: str) -> tuple[str, str]:
    words = [word for word in re.split(r"\s+", line.strip()) if word]
    if not words:
        return "", ""
    if len(words) == 1:
        return words[0], ""
    return words[0], " ".join(words[1:])


def _guess_name(lines: list[str]) -> tuple[str, str]:
    for line in lines[:8]:
        if _looks_like_person_name(line):
            return _split_person_name(line)
    return "", ""


def _guess_job_title(header_lines: list[str], first_name: str, last_name: str) -> str:
    full_name = f"{first_name} {last_name}".strip()
    for line in header_lines[:8]:
        if full_name and line.strip() == full_name:
            continue
        if _looks_like_contact(line) or _detect_section(line):
            continue
        if _looks_like_job_title(line):
            return line.strip()[:80]

    found_name = False
    for line in header_lines[:8]:
        if full_name and line.strip() == full_name:
            found_name = True
            continue
        if found_name and not _looks_like_contact(line) and not _detect_section(line):
            if len(line.strip()) < 90 and not _looks_like_person_name(line):
                return line.strip()[:80]
    return ""


def _normalize_identity_fields(identity: dict[str, Any], raw_text: str, header_lines: list[str]) -> dict[str, Any]:
    result = dict(identity)
    phones = _extract_phones(raw_text)
    if phones:
        result["phone"] = phones

    first = str(result.get("firstName") or "").strip()
    last = str(result.get("lastName") or "").strip()
    title = str(result.get("title") or "").strip()
    full_name = f"{first} {last}".strip()

    if not first and not last and title and _looks_like_person_name(title):
        first, last = _split_person_name(title)
        title = ""

    if full_name and _looks_like_job_title(full_name) and title and _looks_like_person_name(title):
        first, last = _split_person_name(title)
        title = full_name
        full_name = f"{first} {last}".strip()

    if full_name and _looks_like_job_title(full_name) and not title:
        title = full_name
        first, last = _guess_name(header_lines or [line.strip() for line in raw_text.splitlines() if line.strip()])

    if not first and not last:
        first, last = _guess_name(header_lines or [line.strip() for line in raw_text.splitlines() if line.strip()])
        full_name = f"{first} {last}".strip()

    if not title:
        title = _guess_job_title(header_lines, first, last)

    if title and full_name and title.strip().lower() == full_name.strip().lower():
        title = _guess_job_title(header_lines, first, last)

    result["firstName"] = first[:80]
    result["lastName"] = last[:80]
    result["title"] = title[:80]
    return result


def _parse_skills(lines: list[str]) -> list[dict[str, Any]]:
    joined = " ".join(line for line in lines if line and not _detect_section(line))
    chunks = re.split(r"[,;|•\n]", joined)
    skills: list[dict[str, Any]] = []
    seen: set[str] = set()
    for chunk in chunks:
        name = re.sub(r"^[\-•*▪▫◦]\s*", "", chunk).strip()
        if len(name) < 2 or len(name) > 48:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        skills.append({"id": _new_id("sk"), "name": name, "level": 70})
        if len(skills) >= 20:
            break
    return skills


def _parse_languages(lines: list[str]) -> list[dict[str, Any]]:
    languages: list[dict[str, Any]] = []
    for line in lines:
        cleaned = BULLET.sub("", line).strip()
        if not cleaned:
            continue
        parts = re.split(r"\s*[-–—:]\s*", cleaned, maxsplit=1)
        name = parts[0].strip()
        level = parts[1].strip() if len(parts) > 1 else ""
        if name:
            languages.append({"id": _new_id("lg"), "name": name, "level": level})
    return languages[:8]


def _parse_education(lines: list[str]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for line in lines:
        cleaned = BULLET.sub("", line).strip()
        if not cleaned or _detect_section(cleaned):
            continue
        year_match = YEAR_ONLY.search(cleaned)
        year = year_match.group(0) if year_match else ""
        diploma = cleaned
        school = ""
        if " - " in cleaned:
            diploma, school = [part.strip() for part in cleaned.split(" - ", 1)]
        elif " | " in cleaned:
            diploma, school = [part.strip() for part in cleaned.split(" | ", 1)]
        items.append(
            {
                "id": _new_id("ed"),
                "diploma": diploma[:120],
                "school": school[:120],
                "year": year,
                "details": "",
            }
        )
    return items[:8]


def _parse_experiences(lines: list[str]) -> list[dict[str, Any]]:
    merged_lines: list[str] = []
    for line in lines:
        if DATE_RANGE.search(line) and merged_lines and not DATE_RANGE.search(merged_lines[-1]):
            merged_lines.append(line)
        elif DATE_RANGE.search(line) and merged_lines and DATE_RANGE.search(merged_lines[-1]):
            merged_lines.append(line)
        else:
            merged_lines.append(line)

    blocks: list[list[str]] = []
    current: list[str] = []
    for line in merged_lines:
        is_bullet = bool(BULLET.match(line) or line.startswith("- "))
        if DATE_RANGE.search(line) and current and not is_bullet:
            if any(DATE_RANGE.search(item) for item in current):
                blocks.append(current)
                current = [line]
            else:
                current.append(line)
        elif not is_bullet and current and any(DATE_RANGE.search(item) for item in current):
            blocks.append(current)
            current = [line]
        else:
            current.append(line)
    if current:
        blocks.append(current)

    consolidated: list[list[str]] = []
    for block in blocks:
        if consolidated and not any(DATE_RANGE.search(line) for line in block):
            consolidated[-1].extend(block)
        else:
            consolidated.append(block)
    blocks = consolidated

    if not blocks:
        blocks = [[line] for line in lines if line]

    experiences: list[dict[str, Any]] = []
    for block in blocks:
        if not block:
            continue
        title = ""
        company = ""
        location = ""
        start = ""
        end = ""
        current_role = False
        bullets: list[str] = []

        date_line_idx = next((i for i, line in enumerate(block) if DATE_RANGE.search(line)), -1)
        if date_line_idx >= 0:
            date_line = block[date_line_idx]
            match = DATE_RANGE.search(date_line)
            if match:
                start = match.group("start") or ""
                end_raw = (match.group("end") or "").lower()
                current_role = end_raw in {"présent", "present", "aujourd'hui", "actuel", "current"}
                end = "" if current_role else match.group("end") or ""
            before = [line for line in block[:date_line_idx] if line.strip()]
            after = [line for line in block[date_line_idx + 1 :] if line.strip()]
            if before:
                title = before[0]
                if len(before) > 1:
                    company = before[1]
                elif " - " in before[0]:
                    title, company = [part.strip() for part in before[0].split(" - ", 1)]
                elif " | " in before[0]:
                    title, company = [part.strip() for part in before[0].split(" | ", 1)]
            if not title and after:
                title = after[0]
                after = after[1:]
            for line in after:
                cleaned = BULLET.sub("", line).strip()
                if not cleaned:
                    continue
                if BULLET.match(line) or line.startswith("- "):
                    bullets.append(cleaned)
                elif not company and len(cleaned) < 80 and not bullets:
                    company = cleaned
                else:
                    bullets.append(cleaned)
        else:
            title = block[0]
            for line in block[1:]:
                cleaned = BULLET.sub("", line).strip()
                if not cleaned:
                    continue
                if BULLET.match(line) or line.startswith("- "):
                    bullets.append(cleaned)
                elif not company and len(cleaned) < 80 and not bullets:
                    company = cleaned
                else:
                    bullets.append(cleaned)

        if not title and not company and not bullets:
            continue

        experiences.append(
            {
                "id": _new_id("exp"),
                "title": title[:120],
                "company": company[:120],
                "location": location[:80],
                "start": start[:20],
                "end": end[:20],
                "current": current_role,
                "bullets": bullets[:8],
            }
        )
    return experiences[:12]


def _sanitize_parsed_payload(payload: dict[str, Any], raw_text: str) -> dict[str, Any]:
    result = json.loads(json.dumps(payload))
    sections = _split_sections(raw_text)
    identity = _normalize_identity_fields(
        dict(result.get("identity") or {}),
        raw_text,
        sections["header"],
    )

    email_match = EMAIL.search(raw_text)
    if email_match and not identity.get("email"):
        identity["email"] = email_match.group(0)

    summary = (result.get("summary") or "").strip()
    if len(summary) > 700 and len(summary) > len(raw_text) * 0.45:
        result["summary"] = ""

    for key in ("experiences", "education", "skills", "languages", "projects", "certifications", "interests"):
        items = list(result.get(key) or [])
        normalized: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            row = dict(item)
            if not row.get("id"):
                prefix = {
                    "experiences": "exp",
                    "education": "ed",
                    "skills": "sk",
                    "languages": "lg",
                    "projects": "pr",
                    "certifications": "ce",
                    "interests": "in",
                }.get(key, "it")
                row["id"] = _new_id(prefix)
            if key == "experiences":
                row["bullets"] = [str(b).strip() for b in row.get("bullets") or [] if str(b).strip()][:8]
            normalized.append(row)
        result[key] = normalized

    result["identity"] = identity
    return result


def local_parse_imported_cv(text: str, file_name: str = "") -> dict[str, Any]:
    sections = _split_sections(text)
    header_lines = sections["header"]
    all_lines = [line.strip() for line in text.splitlines() if line.strip()]
    first_name, last_name = _guess_name(header_lines or all_lines)
    contact = _parse_contact_fields(text, header_lines)
    title_line = _guess_job_title(header_lines, first_name, last_name)

    summary = " ".join(sections["summary"]).strip()[:900]
    if not summary:
        profile_lines = []
        for line in header_lines:
            if line == f"{first_name} {last_name}".strip() or line == title_line:
                continue
            if _looks_like_contact(line) or _detect_section(line):
                continue
            if len(line) > 40:
                profile_lines.append(line)
        summary = " ".join(profile_lines[:3]).strip()[:900]

    payload = {
        "templateId": "import-original",
        "title": (file_name.rsplit(".", 1)[0] if file_name else "CV importé")[:120],
        "summary": summary,
        "identity": {
            "firstName": first_name,
            "lastName": last_name,
            "title": title_line[:80],
            "email": contact["email"],
            "phone": contact["phone"],
            "location": contact["location"],
            "photo": None,
            "website": contact["website"],
            "github": contact["github"],
        },
        "experiences": _parse_experiences(sections["experience"]),
        "education": _parse_education(sections["education"]),
        "skills": _parse_skills(sections["skills"]),
        "languages": _parse_languages(sections["languages"]),
        "projects": [],
        "certifications": [],
        "interests": [],
    }
    return _sanitize_parsed_payload(payload, text)


async def gemini_parse_imported_cv(text: str, file_name: str = "") -> Optional[dict[str, Any]]:
    if not settings.gemini_enabled or not settings.gemini_api_key:
        return None

    prompt = f"""Tu extrais un CV brut en JSON structuré pour l'éditeur Nogalix.
Ta mission est de PLACER chaque information du document dans le bon champ, sans mélanger les sections.

Réponds UNIQUEMENT en JSON valide :
{{
  "title": "",
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

Règles strictes :
- Lis le texte ligne par ligne et respecte la structure du CV source.
- Le champ summary contient uniquement le profil ou l'accroche (2 à 5 phrases max), jamais tout le CV.
- Chaque expérience professionnelle va dans experiences avec titre, entreprise, dates et puces.
- Chaque diplôme va dans education.
- Les compétences techniques et savoir faire vont dans skills.
- Les langues vont dans languages.
- Sépare correctement prénom et nom dans identity.firstName / identity.lastName.
- identity.title contient uniquement le titre professionnel ou l'intitulé de poste, jamais le nom de la personne.
- identity.phone peut contenir plusieurs numéros séparés par " | " si le CV en liste plusieurs.
- Ne confonds jamais le nom de la personne avec le titre professionnel.
- Ne déplace pas une expérience dans summary ni une compétence dans experiences.
- N'invente aucune information absente du texte source.
- N'utilise aucun texte d'offre d'emploi : extrais uniquement le contenu du CV.
- Français professionnel.
- Ne jamais utiliser le tiret comme ponctuation dans les textes affichés.

Nom du fichier : {file_name or "CV importé"}

Texte du CV :
{text[:12000]}
"""

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent"
    )
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": max(int(settings.gemini_max_output_tokens or 512), 3072),
            "temperature": 0.2,
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
        return _sanitize_parsed_payload(parsed, text)
    except Exception:
        return None


async def parse_imported_cv(text: str, file_name: str = "") -> dict[str, Any]:
    ai = await gemini_parse_imported_cv(text, file_name)
    if ai:
        ai["templateId"] = "import-original"
        return {"payload": ai, "source": "ai"}
    payload = local_parse_imported_cv(text, file_name)
    return {"payload": payload, "source": "local"}


def finalize_import_payload(cv: dict[str, Any]) -> dict[str, Any]:
    """Conserve uniquement le contenu extrait du CV importé, sans texte d'offre."""
    result = json.loads(json.dumps(cv))
    result["templateId"] = "import-original"
    result["principal"] = False
    result["editorStatus"] = "draft"
    return result
