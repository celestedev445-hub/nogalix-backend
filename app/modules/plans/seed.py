from sqlalchemy.orm import Session

from app.modules.plans.catalog import (
    capabilities_for_tier,
    default_plans,
    features_for_tier,
    tier_for_level,
    tier_for_slug,
)
from app.modules.plans.models import Plan, PlanFeature, PlanLimitation


def seed_plan_children(plan: Plan, *, clear: bool = False) -> None:
    tier = tier_for_slug(plan.slug) if plan.slug else tier_for_level(plan.level)
    if clear:
        plan.limitations.clear()
        plan.features.clear()

    existing_keys = {item.key for item in plan.limitations}
    for cap in capabilities_for_tier(tier):
        if cap["key"] in existing_keys:
            continue
        plan.limitations.append(
            PlanLimitation(
                key=cap["key"],
                limitation_type=cap["limitation_type"],
                value=int(cap["value"]),
                description=cap.get("description"),
            )
        )

    if not plan.features:
        for feature in features_for_tier(tier):
            plan.features.append(
                PlanFeature(
                    name=feature["name"],
                    description=feature.get("description"),
                    is_enabled=bool(feature.get("is_enabled", True)),
                    sort_order=int(feature.get("sort_order", 0)),
                )
            )


def ensure_default_plans(db: Session) -> list[Plan]:
    created: list[Plan] = []
    for item in default_plans():
        plan = db.query(Plan).filter(Plan.slug == item["slug"]).first()
        if not plan:
            plan = Plan(
                slug=item["slug"],
                name=item["name"],
                description=item.get("description"),
                tagline=item.get("tagline"),
                price=int(item["price"]),
                duration_months=int(item.get("duration_months", 1)),
                level=int(item["level"]),
                is_active=bool(item.get("is_active", True)),
                highlighted=bool(item.get("highlighted", False)),
                popular=bool(item.get("popular", False)),
                cta=item.get("cta") or "Choisir",
            )
            db.add(plan)
            db.flush()
            seed_plan_children(plan)
            created.append(plan)
        else:
            seed_plan_children(plan, clear=False)
    db.commit()
    return created


def get_default_free_plan(db: Session) -> Plan | None:
    ensure_default_plans(db)
    return db.query(Plan).filter(Plan.slug == "gratuit", Plan.is_active.is_(True)).first()
