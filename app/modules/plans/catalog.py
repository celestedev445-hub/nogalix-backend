"""Catalogue des capacités Nogalix (clés de limitations), style CBC."""

from __future__ import annotations

from typing import Any

# -1 = illimité pour les quotas de type count
UNLIMITED = -1

CAPABILITY_LABELS: dict[str, str] = {
    "cv.max": "Nombre de CV",
    "ai.trials": "Actions IA",
    "templates.premium": "Modèles premium",
    "analyse.advanced": "Analyse IA",
    "assistant.voice": "Édition CV à la voix",
    "documents.letters": "Lettres de motivation",
    "candidature.generate": "Candidature ciblée (CV adapté)",
    "emploi.search": "Recherche d'offres",
    "export.word": "Export Word",
    "support.priority": "Support prioritaire",
}

# Fonctionnalités IA partagées dans le quota ai.trials
AI_TRIAL_KEYS = frozenset(
    {
        "analyse.advanced",
        "assistant.voice",
        "documents.letters",
        "candidature.generate",
    }
)

TIER_GRATUIT = "gratuit"
TIER_PRO = "pro"
TIER_PREMIUM = "premium"


def capability_keys() -> list[str]:
    return list(CAPABILITY_LABELS.keys())


def is_capability_key(key: str) -> bool:
    return key in CAPABILITY_LABELS


def default_plans() -> list[dict[str, Any]]:
    return [
        {
            "slug": "gratuit",
            "name": "Gratuit",
            "description": "Pour commencer : 1 CV, conversion et 3 essais IA, sans carte bancaire.",
            "price": 0,
            "duration_months": 1,
            "is_active": True,
            "level": 1,
            "highlighted": False,
            "cta": "Commencer",
            "tagline": "Pour commencer",
        },
        {
            "slug": "pro",
            "name": "Pro",
            "description": "Pour travailler vraiment : CV illimités, tous les modèles et 30 actions IA par mois.",
            "price": 4900,
            "duration_months": 1,
            "is_active": True,
            "level": 2,
            "highlighted": True,
            "cta": "Choisir Pro",
            "tagline": "Pour aller plus loin",
        },
        {
            "slug": "premium",
            "name": "Premium",
            "description": "Pour se démarquer : IA illimitée, offres d'emploi et support prioritaire.",
            "price": 9900,
            "duration_months": 1,
            "is_active": True,
            "level": 3,
            "highlighted": False,
            "cta": "Choisir Premium",
            "tagline": "Pour se démarquer",
            "popular": True,
        },
    ]


def tier_for_level(level: int) -> str:
    if level <= 1:
        return TIER_GRATUIT
    if level == 2:
        return TIER_PRO
    return TIER_PREMIUM


def tier_for_slug(slug: str) -> str:
    normalized = (slug or "").strip().lower()
    if normalized in {TIER_GRATUIT, "free", "basic"}:
        return TIER_GRATUIT
    if normalized == TIER_PRO:
        return TIER_PRO
    return TIER_PREMIUM


def capabilities_for_tier(tier: str) -> list[dict[str, Any]]:
    """Retourne les limitations seedées pour un palier."""
    catalogs = {
        TIER_GRATUIT: {
            "cv.max": ("count", 1, "1 CV maximum"),
            "ai.trials": ("count", 3, "3 essais IA (analyse, candidature, voix, traduction, assistant)"),
            "templates.premium": ("boolean", 0, "Modèles standards uniquement"),
            "analyse.advanced": ("boolean", 1, "Analyse IA dans le quota d'essais"),
            "assistant.voice": ("boolean", 1, "Voix et assistant dans le quota d'essais"),
            "documents.letters": ("boolean", 1, "Lettres dans le quota d'essais"),
            "candidature.generate": ("boolean", 1, "CV adapté dans le quota d'essais"),
            "emploi.search": ("boolean", 0, "Offres d'emploi réservées au Premium"),
            "export.word": ("boolean", 0, "Export PDF uniquement"),
            "support.priority": ("boolean", 0, "Support standard"),
        },
        TIER_PRO: {
            "cv.max": ("count", UNLIMITED, "CV illimités"),
            "ai.trials": ("count", 30, "30 actions IA par mois"),
            "templates.premium": ("boolean", 1, "Tous les modèles premium"),
            "analyse.advanced": ("boolean", 1, "Analyse IA"),
            "assistant.voice": ("boolean", 1, "Édition CV à la voix"),
            "documents.letters": ("boolean", 1, "Lettres de motivation"),
            "candidature.generate": ("boolean", 1, "CV adapté à une offre"),
            "emploi.search": ("boolean", 0, "Offres d'emploi réservées au Premium"),
            "export.word": ("boolean", 1, "Export PDF et Word"),
            "support.priority": ("boolean", 0, "Support standard"),
        },
        TIER_PREMIUM: {
            "cv.max": ("count", UNLIMITED, "CV illimités"),
            "ai.trials": ("count", UNLIMITED, "Actions IA illimitées"),
            "templates.premium": ("boolean", 1, "Tous les modèles premium"),
            "analyse.advanced": ("boolean", 1, "Analyse ATS"),
            "assistant.voice": ("boolean", 1, "Édition CV à la voix"),
            "documents.letters": ("boolean", 1, "Lettres de motivation"),
            "candidature.generate": ("boolean", 1, "CV adapté à une offre"),
            "emploi.search": ("boolean", 1, "Recherche d'offres"),
            "export.word": ("boolean", 1, "Export PDF et Word"),
            "support.priority": ("boolean", 1, "Support prioritaire"),
        },
    }
    source = catalogs.get(tier) or catalogs[TIER_GRATUIT]
    rows: list[dict[str, Any]] = []
    for key, (lim_type, value, description) in source.items():
        rows.append(
            {
                "key": key,
                "limitation_type": lim_type,
                "value": value,
                "description": description,
            }
        )
    return rows


def features_for_tier(tier: str) -> list[dict[str, Any]]:
    catalogs = {
        TIER_GRATUIT: [
            ("1 CV", "Créez et éditez un CV principal"),
            ("Modèles standards", "Accès aux modèles non premium"),
            ("Convertir PDF et Word", "Conversion publique, sans compte"),
            ("3 essais IA", "Analyse, candidature, voix, traduction et assistant"),
            ("Checklist candidature", "À partir d'une offre collée, sans quota"),
            ("Export PDF", "Impression et export depuis l'éditeur"),
        ],
        TIER_PRO: [
            ("CV illimités", "Créez autant de versions que nécessaire"),
            ("Tous les modèles", "Galerie complète, y compris premium"),
            ("Convertir PDF et Word", "Même conversion que l'éditeur"),
            ("30 actions IA par mois", "Analyse, candidature, voix, traduction, assistant"),
            ("Candidature ciblée", "CV adapté et lettre depuis une offre"),
            ("Édition à la voix", "Complétez votre CV en dictant"),
            ("Export PDF et Word", "Formats adaptés aux recruteurs"),
        ],
        TIER_PREMIUM: [
            ("Tout dans Pro", "CV illimités, modèles et exports"),
            ("IA illimitée", "Plus de plafond sur les actions IA"),
            ("Offres d'emploi", "Matching des postes selon votre CV"),
            ("Support prioritaire", "Réponses prioritaires de l'équipe"),
        ],
    }
    rows = catalogs.get(tier) or catalogs[TIER_GRATUIT]
    return [
        {"name": name, "description": description, "sort_order": index, "is_enabled": True}
        for index, (name, description) in enumerate(rows)
    ]


# Aligné sur frontend templatePreviews (premium: true)
PREMIUM_TEMPLATE_IDS = {
    "mbarga",
    "enzo-dark",
    "voundi-dark",
    "essomba",
}


def template_is_premium(template_id: str) -> bool:
    return (template_id or "").strip().lower() in PREMIUM_TEMPLATE_IDS
