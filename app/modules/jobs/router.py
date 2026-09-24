"""Endpoints recherche d'offres."""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, get_optional_user
from app.core.limiter import limiter
from app.core.responses import ok
from app.modules.jobs.ai_match import cv_profile_text, gemini_rank_jobs
from app.modules.jobs.combined import search_combined
from app.modules.jobs.jsearch import search_jsearch
from app.modules.jobs.limits import JOB_MAX_AGE_DAYS, clamp_max_days_old
from app.modules.jobs.schemas import JobMatchRequest
from app.modules.plans.capability import ensure_capability
from app.modules.users.models import User

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _redact_jobs_for_guest(data: dict[str, Any]) -> dict[str, Any]:
    """Liste publique : titre / lieu / contrat, sans entreprise, source ni détail."""
    jobs = []
    for job in data.get("jobs") or []:
        if not isinstance(job, dict):
            continue
        jobs.append(
            {
                "id": job.get("id"),
                "title": job.get("title") or "Offre",
                "company": "",
                "location": job.get("location") or "",
                "remote": bool(job.get("remote")),
                "contract": job.get("contract") or "CDI",
                "source": "",
                "url": "",
                "salary": None,
                "postedAt": job.get("postedAt") or "",
                "tags": [],
                "summary": "",
            }
        )
    payload = dict(data)
    payload["jobs"] = jobs
    payload["revealed"] = False
    return payload


@router.get("/search")
@limiter.limit("30/minute")
async def search_jobs(
    request: Request,
    q: str = Query(default="", max_length=200),
    where: str = Query(default="", max_length=120),
    page: int = Query(default=1, ge=1, le=50),
    contract: str = Query(default="", max_length=20),
    remote: bool = Query(default=False),
    max_days_old: int | None = Query(
        default=None,
        ge=1,
        le=JOB_MAX_AGE_DAYS,
        description=f"Âge max des offres en jours (1–{JOB_MAX_AGE_DAYS}, défaut {JOB_MAX_AGE_DAYS}).",
    ),
    user: Optional[User] = Depends(get_optional_user),
):
    try:
        data = await search_combined(
            query=q,
            where=where,
            page=page,
            contract=contract,
            remote=remote,
            max_days_old=clamp_max_days_old(max_days_old),
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"message": str(exc)},
        ) from exc
    if not user:
        return ok(_redact_jobs_for_guest(data), message="Offres récupérées.")
    data["revealed"] = True
    return ok(data, message="Offres récupérées.")


@router.get("/search/jsearch")
@limiter.limit("30/minute")
async def search_jobs_jsearch(
    request: Request,
    q: str = Query(default="", max_length=200),
    where: str = Query(default="", max_length=120),
    page: int = Query(default=1, ge=1, le=50),
    contract: str = Query(default="", max_length=20),
    remote: bool = Query(default=False),
    max_days_old: int | None = Query(
        default=None,
        ge=1,
        le=JOB_MAX_AGE_DAYS,
        description=f"Âge max des offres en jours (1–{JOB_MAX_AGE_DAYS}, défaut {JOB_MAX_AGE_DAYS}).",
    ),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Même contrat que `/jobs/search`, mais alimenté par JSearch (RapidAPI)."""
    ensure_capability(
        db,
        user,
        "emploi.search",
        "La recherche d'offres est réservée au plan Premium.",
    )
    try:
        data = await search_jsearch(
            query=q,
            where=where,
            page=page,
            contract=contract,
            remote=remote,
            max_days_old=clamp_max_days_old(max_days_old),
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"message": str(exc)},
        ) from exc
    return ok(data, message="Offres récupérées.")


@router.post("/match")
@limiter.limit("30/minute")
async def match_jobs(
    request: Request,
    body: JobMatchRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Classe un lot d'offres par pertinence réelle vis-à-vis du CV, via l'IA.

    Repli explicite côté front sur le score local si `source` vaut "local"
    (IA indisponible/désactivée) — on ne bloque jamais la recherche pour ça.
    """
    ensure_capability(
        db,
        user,
        "emploi.search",
        "La recherche d'offres est réservée au plan Premium.",
    )
    if not body.jobs:
        return ok({"scores": {}, "source": "none"})

    from app.modules.plans.capability import ensure_ai_trial

    ensure_ai_trial(db, user)

    cv_text = cv_profile_text(body.cv.model_dump())
    jobs_payload = [job.model_dump() for job in body.jobs]
    scores = await gemini_rank_jobs(cv_text, jobs_payload)
    if scores is None:
        return ok({"scores": {}, "source": "local"})
    return ok({"scores": scores, "source": "ai"})
