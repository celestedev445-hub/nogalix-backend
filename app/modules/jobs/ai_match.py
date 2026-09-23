"""Classement des offres par pertinence réelle vis-à-vis d'un CV, via l'IA."""

from __future__ import annotations

from typing import Any, Optional

from app.core.ai import ai_json


def cv_profile_text(cv: dict[str, Any]) -> str:
    parts = [
        str(cv.get("jobTitle") or cv.get("title") or ""),
        str(cv.get("summary") or ""),
    ]
    skills = [str(s).strip() for s in (cv.get("skills") or []) if str(s).strip()]
    if skills:
        parts.append("Compétences : " + ", ".join(skills[:25]))
    experiences = [str(e).strip() for e in (cv.get("experiences") or []) if str(e).strip()]
    if experiences:
        parts.append("Expériences : " + " | ".join(experiences[:8]))
    return "\n".join(part for part in parts if part).strip()


def _job_listing_text(jobs: list[dict[str, Any]]) -> str:
    blocks = []
    for job in jobs:
        tags = ", ".join(job.get("tags") or [])
        summary = str(job.get("summary") or "")[:280]
        blocks.append(
            f"### {job['id']}\n"
            f"Poste : {job.get('title', '')}\n"
            f"Entreprise : {job.get('company', '')}\n"
            f"Tags : {tags}\n"
            f"Description : {summary}"
        )
    return "\n\n".join(blocks)


async def gemini_rank_jobs(
    cv_text: str,
    jobs: list[dict[str, Any]],
) -> Optional[dict[str, dict[str, Any]]]:
    """Retourne {job_id: {score, found, missing}} ou None si l'IA est indisponible."""
    if not jobs:
        return {}

    listing = _job_listing_text(jobs)
    prompt = f"""Tu es un expert en recrutement. Voici le profil d'un candidat, puis une liste d'offres d'emploi.

Pour CHAQUE offre listée (identifiée par son id), évalue à quel point elle correspond RÉELLEMENT au
profil : même métier ou métier proche, compétences attendues réellement présentes, séniorité cohérente,
secteur pertinent. Sois strict et honnête : une offre dans un domaine différent, ou qui demande des
compétences totalement absentes du profil, doit avoir un score bas même si quelques mots se recoupent
par coïncidence (ex : le mot "développement" seul ne suffit pas à faire correspondre un développeur
logiciel à un poste de développement commercial).

Réponds UNIQUEMENT en JSON valide, sans texte autour :
{{"scores": [{{"id": "<id exact de l'offre>", "score": 0, "found": ["ce qui correspond déjà"], "missing": ["ce qu'il manque pour bien correspondre"]}}]}}

Règles :
- Un id de la liste ci-dessous = exactement une entrée dans "scores".
- score entier de 0 (aucun rapport) à 100 (correspondance quasi parfaite).
- found / missing : 3 éléments maximum chacun, courts, en français.
- N'invente aucune compétence ou expérience absente du profil.

Profil du candidat :
{cv_text[:4000] or "(profil très court, peu d'informations disponibles)"}

Offres à évaluer :
{listing[:10000]}
"""

    # Timeout par modèle volontairement court : en cas de saturation d'un modèle
    # (silence au lieu d'un 503 propre), on bascule vite sur le suivant plutôt que
    # de brûler tout le budget sur un modèle qui ne répondra pas.
    parsed = await ai_json(prompt, purpose="match", timeout=30.0)
    if not parsed:
        return None
    raw_scores = parsed.get("scores")
    if not isinstance(raw_scores, list):
        return None

    result: dict[str, dict[str, Any]] = {}
    for item in raw_scores:
        if not isinstance(item, dict):
            continue
        job_id = str(item.get("id") or "").strip()
        if not job_id:
            continue
        try:
            score = max(0, min(100, int(item.get("score"))))
        except (TypeError, ValueError):
            continue
        found = [str(x)[:60] for x in (item.get("found") or []) if str(x).strip()][:3]
        missing = [str(x)[:60] for x in (item.get("missing") or []) if str(x).strip()][:3]
        result[job_id] = {"score": score, "found": found, "missing": missing}

    return result or None
