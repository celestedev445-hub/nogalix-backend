"""Catalogue des capacités Nogalix (clés de limitations), style CBC."""

from __future__ import annotations

from typing import Any

# -1 = illimité pour les quotas de type count
UNLIMITED = -1

CAPABILITY_LABELS: dict[str, str] = {
    "cv.max": "Nombre de CV",
    "templates.premium": "Modèles premium",
    "analyse.advanced": "Analyse IA avancée",
    "assistant.voice": "Édition CV à la voix",
    "documents.letters": "Lettres de motivation",
    "candidature.generate": "Candidature ciblée (CV adapté)",
    "emploi.search": "Recherche d'offres IA",
    "export.word": "Export Word",
    "support.priority": "Support prioritaire",
}

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
            "description": "Pour commencer votre CV professionnel sans carte bancaire.",
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
            "description": "Pour aller plus loin : modèles premium, voix et analyses avancées.",
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
            "description": "Pour se démarquer : emploi IA, support prioritaire et quotas élevés.",
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
            "templates.premium": ("boolean", 0, "Modèles standards uniquement"),
            "analyse.advanced": ("boolean", 0, "Analyse IA basique"),
            "assistant.voice": ("boolean", 0, "Édition vocale non incluse"),
            "documents.letters": ("boolean", 0, "Lettres non incluses"),
            "candidature.generate": ("boolean", 0, "Checklist candidature uniquement"),
            "emploi.search": ("boolean", 0, "Offres d'emploi non incluses"),
            "export.word": ("boolean", 0, "Export PDF (impression) uniquement"),
            "support.priority": ("boolean", 0, "Support standard"),
        },
        TIER_PRO: {
            "cv.max": ("count", UNLIMITED, "CV illimités"),
            "templates.premium": ("boolean", 1, "Tous les modèles premium"),
            "analyse.advanced": ("boolean", 1, "Analyse IA avancée"),
            "assistant.voice": ("boolean", 1, "Édition CV à la voix"),
            "documents.letters": ("boolean", 1, "Lettres de motivation"),
            "candidature.generate": ("boolean", 1, "CV adapté à une offre"),
            "emploi.search": ("boolean", 0, "Offres d'emploi réservées au Premium"),
            "export.word": ("boolean", 1, "Export PDF & Word"),
            "support.priority": ("boolean", 0, "Support standard"),
        },
        TIER_PREMIUM: {
            "cv.max": ("count", UNLIMITED, "CV illimités"),
            "templates.premium": ("boolean", 1, "Tous les modèles premium"),
            "analyse.advanced": ("boolean", 1, "Analyse ATS avancée"),
            "assistant.voice": ("boolean", 1, "Édition CV à la voix"),
            "documents.letters": ("boolean", 1, "Lettres de motivation"),
            "candidature.generate": ("boolean", 1, "CV adapté à une offre"),
            "emploi.search": ("boolean", 1, "Recherche d'offres IA"),
            "export.word": ("boolean", 1, "Export PDF & Word"),
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
            ("Analyse IA basique", "Score et pistes d'amélioration"),
            ("Checklist candidature", "À partir d'une offre collée"),
            ("Export PDF", "Via la boîte d'impression du navigateur"),
        ],
        TIER_PRO: [
            ("CV illimités", "Créez autant de versions que nécessaire"),
            ("Tous les modèles premium", "Accès complet à la galerie"),
            ("Analyse IA avancée", "Audit ATS plus précis"),
            ("Candidature ciblée", "CV adapté + lettre depuis une offre"),
            ("Édition à la voix", "Complétez votre CV en dictant"),
            ("Lettres de motivation", "Documents liés à vos candidatures"),
            ("Export PDF & Word", "Formats adaptés aux recruteurs"),
        ],
        TIER_PREMIUM: [
            ("Tout dans Pro", "Toutes les capacités du plan Pro"),
            ("Offres d'emploi IA", "Matching offres selon votre CV"),
            ("Optimisation ATS avancée", "Recommandations ciblées offre par offre"),
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
