"""Génération candidature ciblée (offre → CV / lettre / checklist)."""

from __future__ import annotations

import re
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.modules.candidature.generate import CandidatureAiError, write_deliverables
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
            "detail": "Rédigez une accroche de 3 à 4 lignes qui cite le poste et 2 compétences clés."
            if len(summary) < 80
            else "Accroche présente. Reformulez-la pour mentionner le poste.",
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
            "detail": "Ajoutez 1 à 2 résultats mesurables (%, délais, volume) dans vos expériences."
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

    try:
        result = await write_deliverables(
            offer=offer,
            cv=cv,
            outputs=wanted,
            local_checklist=lambda: _local_checklist(offer, cv),
            job_title=_extract_job_title(offer),
        )
    except CandidatureAiError as exc:
        raise HTTPException(status_code=503, detail={"message": str(exc)}) from exc

    result["capabilities"] = {
        "checklist": True,
        "cv": allows(plan, "candidature.generate"),
        "letter": allows(plan, "documents.letters"),
    }
    return {"message": "Candidature générée", "data": result}
