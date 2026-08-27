from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.modules.plans import capability as caps
from app.modules.plans.catalog import CAPABILITY_LABELS, is_capability_key
from app.modules.plans.models import Plan, PlanFeature, PlanLimitation
from app.modules.plans.schemas import (
    AssignPlanRequest,
    FeatureUpsertRequest,
    LimitationUpsertRequest,
    PlanCreateRequest,
    PlanUpdateRequest,
)
from app.modules.plans.seed import ensure_default_plans, seed_plan_children
from app.modules.users.models import User

router = APIRouter(tags=["plans"])


def _get_plan_or_404(db: Session, plan_id: int) -> Plan:
    plan = (
        db.query(Plan)
        .options(joinedload(Plan.limitations), joinedload(Plan.features))
        .filter(Plan.id == plan_id)
        .first()
    )
    if not plan:
        raise HTTPException(status_code=404, detail={"message": "Plan introuvable."})
    return plan


@router.get("/plans")
def list_public_plans(db: Session = Depends(get_db)):
    ensure_default_plans(db)
    rows = (
        db.query(Plan)
        .options(joinedload(Plan.limitations), joinedload(Plan.features))
        .filter(Plan.is_active.is_(True))
        .order_by(Plan.level.asc())
        .all()
    )
    return {"data": [row.to_dict() for row in rows]}


@router.get("/plans/catalog")
def capability_catalog(_: User = Depends(require_admin)):
    return {
        "data": [
            {"key": key, "label": label}
            for key, label in CAPABILITY_LABELS.items()
        ]
    }


@router.get("/plans/me")
def my_plan(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ensure_default_plans(db)
    plan = caps.get_user_plan(db, user)
    return {
        "data": {
            "plan": caps.plan_summary(plan),
            "capabilities": caps.capabilities_payload(plan),
        }
    }


@router.get("/admin/plans")
def admin_list_plans(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    ensure_default_plans(db)
    rows = (
        db.query(Plan)
        .options(joinedload(Plan.limitations), joinedload(Plan.features))
        .order_by(Plan.level.asc())
        .all()
    )
    return {"data": [row.to_dict() for row in rows]}


@router.post("/admin/plans", status_code=status.HTTP_201_CREATED)
def admin_create_plan(
    body: PlanCreateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    slug = body.slug.strip().lower().replace(" ", "-")
    if db.query(Plan).filter(Plan.slug == slug).first():
        raise HTTPException(status_code=422, detail={"message": "Ce slug de plan existe déjà."})
    plan = Plan(
        slug=slug,
        name=body.name.strip(),
        description=body.description,
        tagline=body.tagline,
        price=body.price,
        duration_months=body.duration_months,
        level=body.level,
        is_active=body.is_active,
        highlighted=body.highlighted,
        popular=body.popular,
        cta=body.cta,
    )
    db.add(plan)
    db.flush()
    if body.seed_catalog:
        seed_plan_children(plan)
    db.commit()
    db.refresh(plan)
    return {"message": "Plan créé", "data": _get_plan_or_404(db, plan.id).to_dict()}


@router.get("/admin/plans/{plan_id}")
def admin_show_plan(plan_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return {"data": _get_plan_or_404(db, plan_id).to_dict()}


@router.put("/admin/plans/{plan_id}")
def admin_update_plan(
    plan_id: int,
    body: PlanUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    plan = _get_plan_or_404(db, plan_id)
    data = body.model_dump(exclude_none=True)
    for key, value in data.items():
        setattr(plan, key, value.strip() if isinstance(value, str) else value)
    db.add(plan)
    db.commit()
    return {"message": "Plan mis à jour", "data": _get_plan_or_404(db, plan_id).to_dict()}


@router.delete("/admin/plans/{plan_id}")
def admin_delete_plan(plan_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    plan = _get_plan_or_404(db, plan_id)
    if plan.slug == "gratuit":
        raise HTTPException(
            status_code=400,
            detail={"message": "Le plan Gratuit ne peut pas être supprimé."},
        )
    db.delete(plan)
    db.commit()
    return {"message": "Plan supprimé"}


@router.post("/admin/plans/{plan_id}/limitations")
def admin_upsert_limitation(
    plan_id: int,
    body: LimitationUpsertRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    plan = _get_plan_or_404(db, plan_id)
    key = body.key.strip()
    if not is_capability_key(key):
        raise HTTPException(
            status_code=422,
            detail={"message": f"Clé de capacité inconnue: {key}"},
        )
    row = next((item for item in plan.limitations if item.key == key), None)
    if not row:
        row = PlanLimitation(plan_id=plan.id, key=key)
        plan.limitations.append(row)
    row.limitation_type = body.limitation_type
    row.value = body.value
    row.description = body.description
    db.add(plan)
    db.commit()
    return {"message": "Limitation enregistrée", "data": _get_plan_or_404(db, plan_id).to_dict()}


@router.delete("/admin/plans/{plan_id}/limitations/{limitation_id}")
def admin_delete_limitation(
    plan_id: int,
    limitation_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    plan = _get_plan_or_404(db, plan_id)
    row = next((item for item in plan.limitations if item.id == limitation_id), None)
    if not row:
        raise HTTPException(status_code=404, detail={"message": "Limitation introuvable."})
    db.delete(row)
    db.commit()
    return {"message": "Limitation supprimée", "data": _get_plan_or_404(db, plan_id).to_dict()}


@router.post("/admin/plans/{plan_id}/features")
def admin_upsert_feature(
    plan_id: int,
    body: FeatureUpsertRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    plan = _get_plan_or_404(db, plan_id)
    row = PlanFeature(
        plan_id=plan.id,
        name=body.name.strip(),
        description=body.description,
        is_enabled=body.is_enabled,
        sort_order=body.sort_order,
    )
    db.add(row)
    db.commit()
    return {"message": "Fonctionnalité ajoutée", "data": _get_plan_or_404(db, plan_id).to_dict()}


@router.put("/admin/plans/{plan_id}/features/{feature_id}")
def admin_update_feature(
    plan_id: int,
    feature_id: int,
    body: FeatureUpsertRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    plan = _get_plan_or_404(db, plan_id)
    row = next((item for item in plan.features if item.id == feature_id), None)
    if not row:
        raise HTTPException(status_code=404, detail={"message": "Fonctionnalité introuvable."})
    row.name = body.name.strip()
    row.description = body.description
    row.is_enabled = body.is_enabled
    row.sort_order = body.sort_order
    db.add(row)
    db.commit()
    return {"message": "Fonctionnalité mise à jour", "data": _get_plan_or_404(db, plan_id).to_dict()}


@router.delete("/admin/plans/{plan_id}/features/{feature_id}")
def admin_delete_feature(
    plan_id: int,
    feature_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    plan = _get_plan_or_404(db, plan_id)
    row = next((item for item in plan.features if item.id == feature_id), None)
    if not row:
        raise HTTPException(status_code=404, detail={"message": "Fonctionnalité introuvable."})
    db.delete(row)
    db.commit()
    return {"message": "Fonctionnalité supprimée", "data": _get_plan_or_404(db, plan_id).to_dict()}


@router.post("/admin/users/{user_id}/plan")
def admin_assign_plan(
    user_id: int,
    body: AssignPlanRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail={"message": "Utilisateur introuvable."})
    plan = _get_plan_or_404(db, body.plan_id)
    user.plan_id = plan.id
    db.add(user)
    db.commit()
    return {
        "message": f"Plan « {plan.name} » assigné",
        "data": {"user_id": user.id, "plan": caps.plan_summary(plan)},
    }
