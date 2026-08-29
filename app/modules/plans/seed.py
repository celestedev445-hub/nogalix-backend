from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.core.database import engine
from app.modules.plans.catalog import (
    capabilities_for_tier,
    default_plans,
    features_for_tier,
    tier_for_level,
    tier_for_slug,
)
from app.modules.plans.models import Plan, PlanFeature, PlanLimitation


def ensure_ai_trial_columns(db: Session) -> None:
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return
    columns = {item["name"] for item in inspector.get_columns("users")}
    statements: list[str] = []
    if "ai_trials_used" not in columns:
        statements.append("ALTER TABLE users ADD COLUMN ai_trials_used INTEGER NOT NULL DEFAULT 0")
    if "ai_trials_period" not in columns:
        statements.append("ALTER TABLE users ADD COLUMN ai_trials_period VARCHAR(16) NULL")
    for statement in statements:
        db.execute(text(statement))
    if statements:
        db.commit()


def seed_plan_children(plan: Plan, *, clear: bool = False, refresh_features: bool = False) -> None:
    tier = tier_for_slug(plan.slug) if plan.slug else tier_for_level(plan.level)
    if clear:
        plan.limitations.clear()
        plan.features.clear()

    by_key = {item.key: item for item in plan.limitations}
    for cap in capabilities_for_tier(tier):
        row = by_key.get(cap["key"])
        if row:
            row.limitation_type = cap["limitation_type"]
            row.value = int(cap["value"])
            row.description = cap.get("description")
            continue
        plan.limitations.append(
            PlanLimitation(
                key=cap["key"],
                limitation_type=cap["limitation_type"],
                value=int(cap["value"]),
                description=cap.get("description"),
            )
        )

    wanted_features = features_for_tier(tier)
    current_names = [item.name for item in plan.features]
    wanted_names = [item["name"] for item in wanted_features]
    if refresh_features or not plan.features or current_names != wanted_names:
        plan.features.clear()
        for feature in wanted_features:
            plan.features.append(
                PlanFeature(
                    name=feature["name"],
                    description=feature.get("description"),
                    is_enabled=bool(feature.get("is_enabled", True)),
                    sort_order=int(feature.get("sort_order", 0)),
                )
            )


def ensure_default_plans(db: Session) -> list[Plan]:
    ensure_ai_trial_columns(db)
    created: list[Plan] = []
    default_slugs = {item["slug"] for item in default_plans()}
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
                level=int(item.get("level", 1)),
                is_active=bool(item.get("is_active", True)),
                highlighted=bool(item.get("highlighted", False)),
                popular=bool(item.get("popular", False)),
                cta=item.get("cta") or "Choisir",
            )
            db.add(plan)
            db.flush()
            seed_plan_children(plan, refresh_features=True)
            created.append(plan)
        else:
            if item.get("description"):
                plan.description = item["description"]
            seed_plan_children(plan, clear=False, refresh_features=plan.slug in default_slugs)
    db.commit()
    return created


def get_default_free_plan(db: Session) -> Plan | None:
    ensure_default_plans(db)
    return db.query(Plan).filter(Plan.slug == "gratuit", Plan.is_active.is_(True)).first()
