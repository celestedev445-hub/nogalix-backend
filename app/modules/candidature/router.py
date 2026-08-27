"""Génération candidature ciblée (offre → CV / lettre / checklist)."""

from __future__ import annotations

import json
import re
import secrets
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.modules.plans.capability import allows, ensure_capability, get_user_plan
from app.modules.users.models import CurriculumVitae, User

router = APIRouter(prefix="/candidature", tags=["candidature"])

STOPWORDS = {
    "dans",
    "avec",
    "pour",
    "votre",
    "nos",
    "des",
    "les",
    "une",
    "est",
    "sont",
    "plus",
    "moins",
    "vous",
    "nous",
    "etre",
    "être",
    "avoir",
    "fait",
    "faire",
    "ainsi",
    "aussi",
    "cette",
    "ces",
    "aux",
    "sur",
    "par",
    "dont",
    "comme",
    "entre",
    "chez",
    "tout",
    "tous",
    "toute",
    "toutes",
    "ans",
    "annee",
    "année",
    "experience",
    "expérience",
    "mission",
    "missions",
    "profil",
    "recherche",
    "candidat",
    "poste",
    "offre",
    "emploi",
    "equipe",
    "équipe",
    "travail",
    "competences",
    "compétences",
}


class GenerateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    offer_text: str = Field(min_length=40, max_length=20000)
    cv_id: Optional[str] = None
    outputs: list[str] = Field(default_factory=list, max_length=6)
    # optional client CV snapshot when local-only / not yet synced
    cv_snapshot: Optional[dict[str, Any]] = None


def _new_id(prefix: str) -> str:
    return f"{prefix}-{secrets.token_hex(4)}"


def _tokenize(text: str) -> list[str]:
    normalized = (
        (text or "")
        .lower()
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    words = re.split(r"[^a-z0-9+.#]+", normalized)
    seen: set[str] = set()
    out: list[str] = []
    for word in words:
        if len(word) < 4 or word in STOPWORDS or word in seen:
            continue
        seen.add(word)
        out.append(word)
        if len(out) >= 24:
            break
    return out


def _extract_job_title(offer: str) -> str:
    lines = [line.strip(" -•\t") for line in offer.splitlines() if line.strip()]
    for line in lines[:8]:
        lower = line.lower()
        if any(token in lower for token in ("cdi", "cdd", "stage", "freelance", "temps", "salaire", "http")):
            continue
        if 8 <= len(line) <= 90:
            return line[:90]
    return "Poste ciblé"


def _extract_company(offer: str) -> Optional[str]:
    match = re.search(
        r"(?:entreprise|soci[eé]t[eé]|chez|company)\s*[:\-–]?\s*([A-ZÀ-Ü][\w &.'-]{2,60})",
        offer,
        re.I,
    )
    if match:
        return match.group(1).strip()
    return None


def _cv_corpus(cv: dict[str, Any]) -> set[str]:
    chunks: list[str] = [
        str(cv.get("title") or ""),
        str(cv.get("summary") or ""),
        str((cv.get("identity") or {}).get("title") or ""),
    ]
    for exp in cv.get("experiences") or []:
        chunks.append(str(exp.get("title") or ""))
        chunks.append(str(exp.get("company") or ""))
        chunks.extend(exp.get("bullets") or [])
    for skill in cv.get("skills") or []:
        chunks.append(str(skill.get("name") or ""))
    return set(_tokenize(" ".join(chunks)))


def _serialize_cv_row(row: CurriculumVitae) -> dict[str, Any]:
    payload = dict(row.payload or {})
    payload.update(
        {
            "id": row.id,
            "templateId": row.template_id,
            "title": row.title,
            "principal": row.principal,
            "completion": row.completion,
        }
    )
    return payload


def _load_cv(db: Session, user: User, cv_id: Optional[str], snapshot: Optional[dict[str, Any]]) -> dict[str, Any]:
    if cv_id:
        row = (
            db.query(CurriculumVitae)
            .filter(CurriculumVitae.id == cv_id, CurriculumVitae.user_id == user.id)
            .first()
        )
        if not row:
            raise HTTPException(status_code=404, detail={"message": "CV introuvable."})
        return _serialize_cv_row(row)
    if snapshot and isinstance(snapshot, dict):
        return snapshot
    parts = (user.name or "").strip().split()
    first = parts[0] if parts else ""
    last = " ".join(parts[1:]) if len(parts) > 1 else ""
    return {
        "title": "CV",
        "summary": "",
        "identity": {
            "firstName": first,
            "lastName": last,
            "title": "",
            "email": user.email or "",
            "phone": user.phone or "",
            "location": user.location or "",
        },
        "experiences": [],
        "education": [],
        "skills": [],
        "languages": [],
        "projects": [],
        "certifications": [],
    }


def _local_checklist(offer: str, cv: dict[str, Any]) -> dict[str, Any]:
    job_tokens = _tokenize(offer)
    corpus = _cv_corpus(cv)
    found = [w for w in job_tokens if w in corpus][:10]
    missing = [w for w in job_tokens if w not in corpus][:10]
    title = _extract_job_title(offer)
    company = _extract_company(offer)
    items = []
    if missing:
        items.append(
            {
                "id": "keywords",
                "label": "Mots-clés à intégrer",
                "ok": False,
                "detail": "Ajoutez dans votre CV : " + ", ".join(missing[:6]),
            }
        )
    else:
        items.append(
            {
                "id": "keywords",
                "label": "Mots-clés alignés",
                "ok": True,
                "detail": "Les termes principaux de l'offre apparaissent déjà dans votre CV.",
            }
        )
    summary = str(cv.get("summary") or "")
    items.append(
        {
            "id": "summary",
            "label": "Accroche ciblée",
            "ok": len(summary) >= 80,
            "detail": "Rédigez une accroche de 3–4 lignes qui cite le poste et 2 compétences clés."
            if len(summary) < 80
            else "Accroche présente — reformulez-la pour mentionner le poste.",
        }
    )
    exps = cv.get("experiences") or []
    quantified = any(
        any(re.search(r"\d", b or "") for b in (exp.get("bullets") or [])) for exp in exps
    )
    items.append(
        {
            "id": "impact",
            "label": "Résultats chiffrés",
            "ok": quantified,
            "detail": "Ajoutez 1–2 résultats mesurables (%, délais, volume) dans vos expériences."
            if not quantified
            else "Bon : des résultats mesurables sont déjà présents.",
        }
    )
    items.append(
        {
            "id": "title",
            "label": "Titre aligné au poste",
            "ok": bool((cv.get("identity") or {}).get("title")),
            "detail": f"Utilisez un titre proche de « {title} ».",
        }
    )
    return {
        "job_title": title,
        "company": company,
        "keywords_found": found,
        "keywords_missing": missing,
        "items": items,
        "summary": (
            f"Checklist pour « {title} »"
            + (f" chez {company}" if company else "")
            + f" : {len(found)} mot(s) déjà couverts, {len(missing)} à renforcer."
        ),
    }


def _local_letter(offer: str, cv: dict[str, Any]) -> dict[str, Any]:
    identity = cv.get("identity") or {}
    name = f"{identity.get('firstName') or ''} {identity.get('lastName') or ''}".strip() or "Candidat"
    role = identity.get("title") or _extract_job_title(offer)
    company = _extract_company(offer) or "votre entreprise"
    title = _extract_job_title(offer)
    missing = _tokenize(offer)
    corpus = _cv_corpus(cv)
    highlights = [w for w in missing if w in corpus][:4] or missing[:4]
    skills_line = ", ".join(highlights) if highlights else "mes compétences clés"
    body = (
        f"Madame, Monsieur,\n\n"
        f"Actuellement {role}, je souhaite rejoindre {company} pour le poste de {title}.\n\n"
        f"Mon parcours m'a permis de développer {skills_line}, en lien direct avec votre annonce. "
        f"Je serai ravi(e) d'échanger sur la manière dont je peux contribuer à vos objectifs.\n\n"
        f"Cordialement,\n{name}"
    )
    return {
        "title": f"Lettre — {title}",
        "body": body,
    }


def _local_cv_variant(offer: str, cv: dict[str, Any]) -> dict[str, Any]:
    job_title = _extract_job_title(offer)
    company = _extract_company(offer)
    tokens = _tokenize(offer)
    corpus = _cv_corpus(cv)
    missing = [w for w in tokens if w not in corpus][:8]
    found = [w for w in tokens if w in corpus][:8]

    identity = dict(cv.get("identity") or {})
    if job_title and job_title != "Poste ciblé":
        identity["title"] = job_title[:80]

    base_summary = (cv.get("summary") or "").strip()
    highlight = ", ".join(found[:4] or tokens[:4])
    target = f"Poste visé : {job_title}" + (f" ({company})" if company else "") + "."
    if base_summary:
        summary = f"{base_summary.rstrip('.')}. {target} Compétences mises en avant : {highlight}."
    else:
        summary = (
            f"Professionnel(le) motivé(e) pour le poste de {job_title}. "
            f"Je mets en avant {highlight}."
        )
    if missing:
        summary += f" Ouvert(e) à renforcer : {', '.join(missing[:4])}."

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
            if tip.lower() not in " ".join(bullets).lower():
                bullets = bullets + [f"Exposition à {tip}, en lien avec le poste ciblé."]
                item["bullets"] = bullets
        experiences.append(item)

    title = f"CV — {job_title}"[:120]
    return {
        "templateId": cv.get("templateId") or "atlas",
        "title": title,
        "principal": False,
        "identity": identity,
        "summary": summary[:1200],
        "experiences": experiences,
        "education": cv.get("education") or [],
        "skills": skills,
        "languages": cv.get("languages") or [],
        "projects": cv.get("projects") or [],
        "certifications": cv.get("certifications") or [],
        "interests": cv.get("interests") or [],
    }


async def _gemini_generate(offer: str, cv: dict[str, Any], outputs: list[str]) -> Optional[dict[str, Any]]:
    if not settings.gemini_enabled or not settings.gemini_api_key:
        return None

    snapshot = json.dumps(
        {
            "title": cv.get("title"),
            "summary": cv.get("summary"),
            "identity": cv.get("identity"),
            "experiences": (cv.get("experiences") or [])[:4],
            "skills": (cv.get("skills") or [])[:12],
            "education": (cv.get("education") or [])[:3],
            "languages": cv.get("languages") or [],
        },
        ensure_ascii=False,
    )[:7000]

    prompt = f"""Tu prépares une candidature Nogalix à partir d'une offre d'emploi et d'un CV.
Réponds UNIQUEMENT en JSON valide (pas de markdown), clés possibles selon outputs demandés: {outputs}.

Schéma:
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
    "templateId":"atlas",
    "title":"",
    "principal": false,
    "identity": {{"firstName":"","lastName":"","title":"","email":"","phone":"","location":""}},
    "summary":"",
    "experiences":[],
    "education":[],
    "skills":[{{"id":"","name":"","level":70}}],
    "languages":[],
    "projects":[],
    "certifications":[],
    "interests":[]
  }}
}}

Règles:
- Français professionnel.
- N'invente pas d'expériences ou diplômes absents du CV ; tu peux reformuler, réordonner, enrichir les puces avec des mots-clés de l'offre.
- Pour letter.body : lettre complète, 180-280 mots max.
- Pour cv : variante adaptée à l'offre (nouvelle version, pas un écrasement conceptuel).
- checklist.items : 4 à 7 points actionnables.

Offre:
{offer[:8000]}

CV (JSON):
{snapshot}
"""

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent"
    )
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": max(int(settings.gemini_max_output_tokens or 512), 2048),
            "temperature": 0.45,
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
        raw = "\n".join(texts).strip()
        match = re.search(r"\{[\s\S]*\}", raw)
        if not match:
            return None
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


@router.post("/generate")
async def generate_candidature(
    body: GenerateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    wanted = [item.strip().lower() for item in body.outputs if item.strip()]
    allowed = {"checklist", "cv", "letter"}
    wanted = [item for item in wanted if item in allowed]
    if not wanted:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Sélectionnez au moins un livrable (checklist, cv, letter)."},
        )

    plan = get_user_plan(db, user)
    if "cv" in wanted:
        ensure_capability(
            db,
            user,
            "candidature.generate",
            "L'adaptation de CV à une offre est incluse à partir du plan Pro.",
        )
    if "letter" in wanted:
        ensure_capability(
            db,
            user,
            "documents.letters",
            "Les lettres de motivation sont incluses à partir du plan Pro.",
        )
    # checklist : gratuit ; si seul livrable payant sans droit déjà filtré ci-dessus

    cv = _load_cv(db, user, body.cv_id, body.cv_snapshot)
    offer = body.offer_text.strip()

    gemini = await _gemini_generate(offer, cv, wanted)
    result: dict[str, Any] = {"source": "gemini" if gemini else "local", "offer_title": _extract_job_title(offer)}

    if "checklist" in wanted:
        result["checklist"] = (gemini or {}).get("checklist") or _local_checklist(offer, cv)
    if "letter" in wanted:
        result["letter"] = (gemini or {}).get("letter") or _local_letter(offer, cv)
    if "cv" in wanted:
        adapted = (gemini or {}).get("cv") if gemini else None
        if not isinstance(adapted, dict) or not adapted.get("summary"):
            adapted = _local_cv_variant(offer, cv)
        else:
            # conserve identité réelle si le modèle a vidé les champs
            identity = dict(cv.get("identity") or {})
            model_id = adapted.get("identity") if isinstance(adapted.get("identity"), dict) else {}
            for key in ("firstName", "lastName", "email", "phone", "location", "photo", "website", "github"):
                if not model_id.get(key) and identity.get(key):
                    model_id[key] = identity.get(key)
            if not model_id.get("title"):
                model_id["title"] = identity.get("title") or _extract_job_title(offer)
            adapted["identity"] = model_id
            adapted["templateId"] = adapted.get("templateId") or cv.get("templateId") or "atlas"
            adapted["principal"] = False
        result["cv"] = adapted

    # Indiquer les capacités restantes pour l'UI
    result["capabilities"] = {
        "checklist": True,
        "cv": allows(plan, "candidature.generate"),
        "letter": allows(plan, "documents.letters"),
    }
    return {"message": "Candidature générée", "data": result}
