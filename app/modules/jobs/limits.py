"""Règles communes aux sources d'offres d'emploi."""

# Plafond global : aucune source ne doit renvoyer d'offres de plus d'un mois.
JOB_MAX_AGE_DAYS = 30


def clamp_max_days_old(value: int | None) -> int:
    """Retourne une fenêtre en jours dans [1, JOB_MAX_AGE_DAYS], défaut = 1 mois."""
    if value is None:
        return JOB_MAX_AGE_DAYS
    try:
        days = int(value)
    except (TypeError, ValueError):
        return JOB_MAX_AGE_DAYS
    return max(1, min(days, JOB_MAX_AGE_DAYS))
