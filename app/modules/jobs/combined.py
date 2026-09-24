"""Fusion Adzuna + JSearch pour une seule liste d'offres."""

from __future__ import annotations

import asyncio
from typing import Any

from app.core.config import settings
from app.modules.jobs.adzuna import search_adzuna
from app.modules.jobs.jsearch import search_jsearch
from app.modules.jobs.limits import JOB_MAX_AGE_DAYS, clamp_max_days_old

# JSearch est souvent lent : on ne bloque pas toute la page Emploi derrière.
JSEARCH_COMBINED_TIMEOUT = 22.0


def _job_key(job: dict[str, Any]) -> str:
    title = str(job.get("title") or "").strip().lower()
    company = str(job.get("company") or "").strip().lower()
    return f"{title}|{company}"


def _interleave(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    merged: list[dict[str, Any]] = []
    i = j = 0
    while i < len(left) or j < len(right):
        if i < len(left):
            key = _job_key(left[i])
            if key not in seen:
                seen.add(key)
                merged.append(left[i])
            i += 1
        if j < len(right):
            key = _job_key(right[j])
            if key not in seen:
                seen.add(key)
                merged.append(right[j])
            j += 1
    return merged


async def _safe_jsearch(**kwargs: Any) -> dict[str, Any] | None:
    if not (settings.rapidapi_key or "").strip():
        return None
    try:
        return await asyncio.wait_for(search_jsearch(**kwargs), timeout=JSEARCH_COMBINED_TIMEOUT)
    except Exception:
        return None


async def search_combined(
    *,
    query: str,
    where: str = "",
    page: int = 1,
    contract: str = "",
    remote: bool = False,
    max_days_old: int | None = None,
) -> dict[str, Any]:
    days = clamp_max_days_old(max_days_old)
    common = {
        "query": query,
        "where": where,
        "page": page,
        "contract": contract,
        "remote": remote,
        "max_days_old": days,
    }

    adzuna_task = asyncio.create_task(
        search_adzuna(**common, results_per_page=20),
    )
    jsearch_task = asyncio.create_task(_safe_jsearch(**common))

    adzuna_raw, jsearch_raw = await asyncio.gather(adzuna_task, jsearch_task, return_exceptions=True)

    adzuna = adzuna_raw if isinstance(adzuna_raw, dict) else None
    jsearch = jsearch_raw if isinstance(jsearch_raw, dict) else None
    adzuna_error = adzuna_raw if isinstance(adzuna_raw, Exception) else None

    if not adzuna and not jsearch:
        if adzuna_error:
            raise adzuna_error
        raise RuntimeError("Aucune source d'offres n'a répondu.")

    adzuna_jobs = list(adzuna.get("jobs") or []) if adzuna else []
    jsearch_jobs = list(jsearch.get("jobs") or []) if jsearch else []
    jobs = _interleave(adzuna_jobs, jsearch_jobs)

    names: list[str] = []
    attributions: list[dict[str, Any]] = []
    if adzuna:
        names.append("Adzuna")
        if adzuna.get("attribution"):
            attributions.append(adzuna["attribution"])
    if jsearch:
        names.append("JSearch")
        if jsearch.get("attribution"):
            attributions.append(jsearch["attribution"])

    count = int((adzuna or {}).get("count") or 0) + int((jsearch or {}).get("count") or 0)
    if adzuna and not jsearch:
        count = int(adzuna.get("count") or len(jobs))
    elif jsearch and not adzuna:
        count = int(jsearch.get("count") or len(jobs))
    elif not count:
        count = len(jobs)

    total_pages = max(
        int(adzuna.get("totalPages") or 1) if adzuna else 1,
        int(jsearch.get("totalPages") or 1) if jsearch else 1,
        1,
    )

    return {
        "jobs": jobs,
        "count": count,
        "page": page,
        "pageSize": max(len(jobs), 1),
        "totalPages": total_pages,
        "maxDaysOld": days,
        "maxAgeDays": JOB_MAX_AGE_DAYS,
        "source": " + ".join(names) if names else "Adzuna",
        "sources": names,
        "attribution": attributions[0] if len(attributions) == 1 else attributions,
    }
