from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.modules.plans.catalog import (
    CAPABILITY_LABELS,
    UNLIMITED,
    capabilities_for_tier,
    template_is_premium,
    tier_for_level,
)
from app.modules.plans.models import Plan, PlanLimitation
from app.modules.users.models import CurriculumVitae, User


def get_user_plan(db: Session, user: User) -> Optional[Plan]:
    if not user.plan_id:
        return (
            db.query(Plan)
            .options(joinedload(Plan.limitations), joinedload(Plan.features))
            .filter(Plan.slug == "gratuit", Plan.is_active.is_(True))
            .first()
        )
    return (
        db.query(Plan)
        .options(joinedload(Plan.limitations), joinedload(Plan.features))
        .filter(Plan.id == user.plan_id)
        .first()
    )


def _limitation_map(plan: Optional[Plan]) -> dict[str, PlanLimitation]:
    if not plan:
        return {}
    return {item.key: item for item in plan.limitations}


def get_count_limit(plan: Optional[Plan], key: str, default: int = 0) -> int:
    row = _limitation_map(plan).get(key)
    if not row:
        # Fallback catalogue selon level
        if plan:
            for cap in capabilities_for_tier(tier_for_level(plan.level)):
                if cap["key"] == key and cap["limitation_type"] == "count":
                    return int(cap["value"])
        return default
    return int(row.value)


def allows(plan: Optional[Plan], key: str, default: bool = False) -> bool:
    row = _limitation_map(plan).get(key)
    if not row:
        if plan:
            for cap in capabilities_for_tier(tier_for_level(plan.level)):
                if cap["key"] == key:
                    if cap["limitation_type"] == "boolean":
                        return int(cap["value"]) > 0
                    return int(cap["value"]) != 0
        return default
    if row.limitation_type == "boolean":
        return int(row.value) > 0
    return int(row.value) != 0


def capabilities_payload(plan: Optional[Plan]) -> dict:
    result: dict[str, dict] = {}
    for key, label in CAPABILITY_LABELS.items():
        row = _limitation_map(plan).get(key)
        if row:
            lim_type = row.limitation_type
            value = int(row.value)
        else:
            # defaults from tier
            value = 0
            lim_type = "boolean"
            if plan:
                for cap in capabilities_for_tier(tier_for_level(plan.level)):
                    if cap["key"] == key:
                        lim_type = cap["limitation_type"]
                        value = int(cap["value"])
                        break
        allowed = value > 0 if lim_type == "boolean" else value == UNLIMITED or value > 0
        result[key] = {
            "label": label,
            "type": lim_type,
            "value": value,
            "allowed": allowed,
            "unlimited": lim_type == "count" and value == UNLIMITED,
        }
    return result


def plan_summary(plan: Optional[Plan]) -> Optional[dict]:
    if not plan:
        return None
    return {
        "id": plan.id,
        "slug": plan.slug,
        "name": plan.name,
        "level": plan.level,
        "price": plan.price,
    }


def ensure_can_create_cv(db: Session, user: User) -> None:
    plan = get_user_plan(db, user)
    limit = get_count_limit(plan, "cv.max", default=1)
    if limit == UNLIMITED:
        return
    count = db.query(CurriculumVitae).filter(CurriculumVitae.user_id == user.id).count()
    if count >= limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": f"Votre plan {plan.name if plan else 'Gratuit'} autorise {limit} CV. Passez à Pro pour en créer davantage.",
                "code": "plan_limit_cv",
                "capability": "cv.max",
                "limit": limit,
            },
        )


def ensure_can_use_template(db: Session, user: User, template_id: str) -> None:
    if not template_is_premium(template_id):
        return
    plan = get_user_plan(db, user)
    if allows(plan, "templates.premium"):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "message": "Ce modèle est réservé aux plans Pro et Premium.",
            "code": "plan_limit_template",
            "capability": "templates.premium",
        },
    )


def ensure_capability(db: Session, user: User, key: str, message: str) -> None:
    plan = get_user_plan(db, user)
    if allows(plan, key):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "message": message,
            "code": f"plan_limit_{key.replace('.', '_')}",
            "capability": key,
            "plan": plan_summary(plan),
        },
    )
