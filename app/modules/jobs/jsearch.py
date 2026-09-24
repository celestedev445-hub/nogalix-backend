"""Client JSearch (RapidAPI) — recherche d'offres agrégées (Google Jobs, LinkedIn, Indeed…).

Renvoie exactement le même format normalisé que `search_adzuna` pour pouvoir
être consommé par le front sans adaptation.
"""

from __future__ import annotations

from typing import Any, Optional

import httpx

from app.core.config import settings
from app.modules.jobs.adzuna import _extract_tags, _is_remote, _is_within_max_age, _strip_html
from app.modules.jobs.limits import JOB_MAX_AGE_DAYS, clamp_max_days_old

# JSearch renvoie 10 offres par page (non paramétrable).
JSEARCH_PAGE_SIZE = 10
# L'API est lente (souvent 30–60 s) : timeout large.
JSEARCH_TIMEOUT_SECONDS = 90.0

EMPLOYMENT_TYPES = {
    "CDI": "FULLTIME",
    "Freelance": "CONTRACTOR",
    "Stage": "INTERN",
}

SALARY_PERIODS = {
    "YEAR": "an",
    "MONTH": "mois",
    "WEEK": "semaine",
    "DAY": "jour",
    "HOUR": "heure",
}


def _date_posted(days: int) -> str:
    if days <= 1:
        return "today"
    if days <= 3:
        return "3days"
    if days <= 7:
        return "week"
    return "month"


def _map_contract(item: dict[str, Any], title: str, description: str) -> str:
    types = [str(t).upper() for t in (item.get("job_employment_types") or [])]
    if not types and item.get("job_employment_type"):
        types = [str(item.get("job_employment_type")).upper()]
    hay = f"{title} {item.get('job_employment_type') or ''}".lower()
    if "INTERN" in types or "stage" in hay or "stagiaire" in hay:
        return "Stage"
    if "cdd" in hay or "cdd" in description.lower()[:300]:
        return "CDD"
    if "CONTRACTOR" in types or "freelance" in hay:
        return "Freelance"
    if "PARTTIME" in types:
        return "CDD"
    return "CDI"


def _format_salary(item: dict[str, Any]) -> Optional[str]:
    low = item.get("job_min_salary")
    high = item.get("job_max_salary")
    if low is None and high is None:
        text = item.get("job_salary_string")
        return str(text) if text else None
    period = SALARY_PERIODS.get(str(item.get("job_salary_period") or "YEAR").upper(), "an")

    def fmt(amount: float) -> str:
        return f"{int(round(amount)):,}".replace(",", " ")

    if low is not None and high is not None and abs(float(high) - float(low)) > 1:
        return f"{fmt(float(low))} – {fmt(float(high))} € / {period}"
    amount = float(high if high is not None else low)
    return f"{fmt(amount)} € / {period}"


def normalize_job(item: dict[str, Any]) -> dict[str, Any]:
    title = _strip_html(str(item.get("job_title") or "Offre"))
    description = _strip_html(str(item.get("job_description") or ""))
    company = str(item.get("employer_name") or "Entreprise confidentielle")
    location = str(item.get("job_location") or item.get("job_city") or "France")
    publisher = str(item.get("job_publisher") or "").strip()
    # job_is_remote est fiable ; la description mentionne souvent "remote" à tort.
    remote = bool(item.get("job_is_remote")) or _is_remote(title, location, "")
    tags = _extract_tags({"category": {"label": publisher}}, description)
    return {
        "id": f"jsearch-{item.get('job_id')}",
        "title": title,
        "company": company,
        "location": location,
        "remote": remote,
        "contract": _map_contract(item, title, description),
        "source": f"JSearch · {publisher}" if publisher else "JSearch",
        "url": str(item.get("job_apply_link") or item.get("job_google_link") or ""),
        "salary": _format_salary(item),
        "postedAt": str(item.get("job_posted_at_datetime_utc") or ""),
        "tags": tags,
        "summary": description[:420] + ("…" if len(description) > 420 else ""),
    }


async def search_jsearch(
    *,
    query: str,
    where: str = "",
    page: int = 1,
    contract: str = "",
    remote: bool = False,
    max_days_old: int | None = None,
) -> dict[str, Any]:
    api_key = (settings.rapidapi_key or "").strip()
    host = (settings.jsearch_host or "jsearch.p.rapidapi.com").strip()
    country = (settings.jsearch_country or "fr").strip().lower() or "fr"

    if not api_key:
        raise RuntimeError("JSearch n'est pas configuré (RAPIDAPI_KEY).")

    page = max(1, min(page, 50))
    what = (query or "").strip() or "emploi"
    contract_key = (contract or "").strip()
    days = clamp_max_days_old(max_days_old)

    if contract_key == "CDD" and "cdd" not in what.lower():
        what = f"{what} CDD"
    full_query = f"{what} in {where.strip()}" if where.strip() else what

    params: dict[str, Any] = {
        "query": full_query,
        "page": page,
        "num_pages": 1,
        "country": country,
        "date_posted": _date_posted(days),
    }
    if contract_key in EMPLOYMENT_TYPES:
        params["employment_types"] = EMPLOYMENT_TYPES[contract_key]
    if remote:
        params["work_from_home"] = "true"

    headers = {"x-rapidapi-key": api_key, "x-rapidapi-host": host}
    try:
        async with httpx.AsyncClient(timeout=JSEARCH_TIMEOUT_SECONDS) as client:
            response = await client.get(f"https://{host}/search-v2", params=params, headers=headers)
    except httpx.TimeoutException as exc:
        raise RuntimeError("JSearch ne répond pas. Réessayez plus tard.") from exc

    if response.status_code in {401, 403}:
        raise RuntimeError("Clé RapidAPI invalide ou abonnement JSearch inactif.")
    if response.status_code == 429:
        raise RuntimeError("Quota JSearch atteint. Réessayez plus tard.")
    if response.status_code >= 400:
        raise RuntimeError(f"JSearch a renvoyé une erreur ({response.status_code}).")

    payload = response.json()
    data = payload.get("data") or {}
    results = data.get("jobs") if isinstance(data, dict) else data
    results = results or []
    jobs = []
    for item in results:
        if not isinstance(item, dict):
            continue
        job = normalize_job(item)
        if _is_within_max_age(str(job.get("postedAt") or ""), days):
            jobs.append(job)

    # JSearch ne fournit pas de total : on suppose une page suivante tant que la page est pleine.
    has_more = len(results) >= JSEARCH_PAGE_SIZE and page < 50
    total_pages = page + 1 if has_more else page
    count = (page - 1) * JSEARCH_PAGE_SIZE + len(jobs) + (JSEARCH_PAGE_SIZE if has_more else 0)

    return {
        "jobs": jobs,
        "count": count,
        "page": page,
        "pageSize": JSEARCH_PAGE_SIZE,
        "totalPages": total_pages,
        "maxDaysOld": days,
        "maxAgeDays": JOB_MAX_AGE_DAYS,
        "source": "JSearch",
        "attribution": {
            "name": "JSearch",
            "url": "https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch",
            "logo": "https://rapidapi.com/favicon.ico",
        },
    }
