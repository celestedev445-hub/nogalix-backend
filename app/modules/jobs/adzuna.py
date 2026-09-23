"""Client Adzuna — recherche d'offres."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from app.core.config import settings
from app.modules.jobs.limits import JOB_MAX_AGE_DAYS, clamp_max_days_old

REMOTE_MARKERS = (
    "remote",
    "télétravail",
    "teletravail",
    "home working",
    "work from home",
    "wfh",
    "full remote",
    "100% remote",
)


def _strip_html(text: str) -> str:
    cleaned = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", cleaned).strip()


def _is_remote(title: str, location: str, description: str) -> bool:
    hay = f"{title} {location} {description}".lower()
    return any(marker in hay for marker in REMOTE_MARKERS)


def _map_contract(raw: Optional[str], category_label: str = "") -> str:
    value = (raw or "").strip().lower()
    label = (category_label or "").lower()
    if "stage" in value or "stage" in label or "internship" in value:
        return "Stage"
    if value in {"permanent", "full_time"}:
        return "CDI"
    if value in {"contract", "temporary", "fixed_term"}:
        return "CDD"
    if value in {"part_time", "freelance", "contractor"}:
        return "Freelance"
    if "cdi" in value:
        return "CDI"
    if "cdd" in value:
        return "CDD"
    return "CDI"


def _format_salary(item: dict[str, Any]) -> Optional[str]:
    low = item.get("salary_min")
    high = item.get("salary_max")
    if low is None and high is None:
        return None
    predicted = str(item.get("salary_is_predicted") or "0") == "1"

    def fmt(amount: float) -> str:
        return f"{int(round(amount)):,}".replace(",", " ")

    if low is not None and high is not None and abs(float(high) - float(low)) > 1:
        text = f"{fmt(float(low))} – {fmt(float(high))} € / an"
    else:
        amount = float(high if high is not None else low)
        text = f"{fmt(amount)} € / an"
    if predicted:
        text = f"{text} (estimé)"
    return text


def _extract_tags(item: dict[str, Any], description: str) -> list[str]:
    tags: list[str] = []
    category = item.get("category") or {}
    label = (category.get("label") or "").strip().replace("Emplois ", "")
    if label:
        tags.append(label)
    for word in (
        "Python",
        "JavaScript",
        "TypeScript",
        "React",
        "Next.js",
        "Node",
        "Java",
        "PHP",
        "Laravel",
        "SQL",
        "AWS",
        "Azure",
        "Docker",
        "Figma",
        "Agile",
    ):
        if word.lower() in description.lower() and word not in tags:
            tags.append(word)
    return tags[:8]


def _is_within_max_age(posted_at: str, max_days: int) -> bool:
    if not posted_at:
        return True
    try:
        # Adzuna renvoie de l'ISO UTC (…Z).
        created = datetime.fromisoformat(posted_at.replace("Z", "+00:00"))
    except ValueError:
        return True
    age = datetime.now(timezone.utc) - created.astimezone(timezone.utc)
    return age.total_seconds() <= (max_days + 1) * 24 * 3600


def normalize_job(item: dict[str, Any]) -> dict[str, Any]:
    company = (item.get("company") or {}).get("display_name") or "Entreprise confidentielle"
    location = (item.get("location") or {}).get("display_name") or "France"
    title = _strip_html(str(item.get("title") or "Offre"))
    description = _strip_html(str(item.get("description") or ""))
    category = item.get("category") or {}
    contract_raw = item.get("contract_type") or item.get("contract_time")
    return {
        "id": f"adzuna-{item.get('id')}",
        "title": title,
        "company": company,
        "location": location,
        "remote": _is_remote(title, location, description),
        "contract": _map_contract(str(contract_raw) if contract_raw else None, str(category.get("label") or "")),
        "source": "Adzuna",
        "url": str(item.get("redirect_url") or item.get("adref") or "https://www.adzuna.fr/"),
        "salary": _format_salary(item),
        "postedAt": str(item.get("created") or ""),
        "tags": _extract_tags(item, description),
        "summary": description[:420] + ("…" if len(description) > 420 else ""),
    }


async def search_adzuna(
    *,
    query: str,
    where: str = "",
    page: int = 1,
    results_per_page: int = 20,
    contract: str = "",
    remote: bool = False,
    max_days_old: int | None = None,
) -> dict[str, Any]:
    app_id = (settings.adzuna_app_id or "").strip()
    app_key = (settings.adzuna_app_key or "").strip()
    country = (settings.adzuna_country or "fr").strip().lower() or "fr"

    if not app_id or not app_key:
        raise RuntimeError("Adzuna n'est pas configuré (ADZUNA_APP_ID / ADZUNA_APP_KEY).")

    page = max(1, min(page, 50))
    results_per_page = max(1, min(results_per_page, 50))
    what = (query or "").strip() or "emploi"
    contract_key = (contract or "").strip()
    # Toujours plafonner à 1 mois (toutes sources confondues).
    days = clamp_max_days_old(max_days_old)

    if contract_key == "Stage" and "stage" not in what.lower():
        what = f"{what} stage".strip()
    if remote and "télétravail" not in what.lower() and "teletravail" not in what.lower() and "remote" not in what.lower():
        what = f"{what} télétravail".strip()

    params: dict[str, Any] = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": results_per_page,
        "content-type": "application/json",
        "max_days_old": days,
    }
    # Adzuna "what" est un ET logique sur chaque mot : au-delà de 3 mots (titre de
    # poste + compétences extraites d'un CV), ça retombe quasi toujours à 0 résultat.
    # "what_or" élargit le vivier ; le score de matching local (matchJobToCv) affine ensuite.
    # Avec what_or, trier par date renvoie une page ~aléatoire vis-à-vis de la requête :
    # on trie par pertinence pour que la page récupérée contienne déjà les offres
    # proches du CV (le tri final affiché reste de toute façon fait par score local).
    if len(what.split()) > 3:
        params["what_or"] = what
        params["sort_by"] = "relevance"
    else:
        params["what"] = what
        params["sort_by"] = "date"
    if where.strip():
        params["where"] = where.strip()
    if contract_key == "CDI":
        params["permanent"] = 1
    elif contract_key in {"CDD", "Freelance"}:
        params["contract"] = 1

    url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(url, params=params)

    if response.status_code == 401:
        raise RuntimeError("Clés Adzuna invalides.")
    if response.status_code == 429:
        raise RuntimeError("Quota Adzuna atteint. Réessayez plus tard.")
    if response.status_code >= 400:
        raise RuntimeError(f"Adzuna a renvoyé une erreur ({response.status_code}).")

    payload = response.json()
    results = payload.get("results") or []
    jobs = []
    for item in results:
        if not isinstance(item, dict):
            continue
        job = normalize_job(item)
        if _is_within_max_age(str(job.get("postedAt") or ""), JOB_MAX_AGE_DAYS) and _is_within_max_age(
            str(job.get("postedAt") or ""), days
        ):
            jobs.append(job)

    count = int(payload.get("count") or len(jobs))
    total_pages = max(1, min(50, (count + results_per_page - 1) // results_per_page)) if count else 1
    if page > total_pages:
        page = total_pages

    return {
        "jobs": jobs,
        "count": count,
        "page": page,
        "pageSize": results_per_page,
        "totalPages": total_pages,
        "maxDaysOld": days,
        "maxAgeDays": JOB_MAX_AGE_DAYS,
        "source": "Adzuna",
        "attribution": {
            "name": "Adzuna",
            "url": "https://www.adzuna.fr/",
            "logo": "https://www.adzuna.fr/favicon.ico",
        },
    }
