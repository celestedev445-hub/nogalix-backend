from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.cv.schemas import CvPayload, compute_completion
from app.modules.users.models import CurriculumVitae, Notification, User


def _serialize(row: CurriculumVitae) -> dict:
    payload = dict(row.payload or {})
    payload.update(
        {
            "id": row.id,
            "templateId": row.template_id,
            "title": row.title,
            "principal": row.principal,
            "completion": row.completion,
            "updatedAt": row.updated_at.isoformat() if row.updated_at else datetime.now(timezone.utc).isoformat(),
        }
    )
    return payload


def list_cvs(db: Session, user: User) -> dict:
    """Frontend unwraps CvData[] | { data: CvData[] }."""
    rows = (
        db.query(CurriculumVitae)
        .filter(CurriculumVitae.user_id == user.id)
        .order_by(CurriculumVitae.updated_at.desc())
        .all()
    )
    data = [_serialize(row) for row in rows]
    return {"data": data}


def get_cv(db: Session, user: User, cv_id: str) -> dict:
    row = (
        db.query(CurriculumVitae)
        .filter(CurriculumVitae.id == cv_id, CurriculumVitae.user_id == user.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail={"message": "CV introuvable."})
    return _serialize(row)


def create_cv(db: Session, user: User, body: CvPayload) -> dict:
    from app.modules.plans.capability import ensure_can_create_cv, ensure_can_use_template

    ensure_can_create_cv(db, user)
    ensure_can_use_template(db, user, body.templateId or "atlas")

    data = body.model_dump(exclude_none=False)
    cv_id = (data.get("id") or "").strip() or str(uuid4())
    if db.query(CurriculumVitae).filter(CurriculumVitae.id == cv_id).first():
        cv_id = str(uuid4())

    if body.principal:
        db.query(CurriculumVitae).filter(
            CurriculumVitae.user_id == user.id,
            CurriculumVitae.principal.is_(True),
        ).update({"principal": False})

    completion = compute_completion(data)
    now = datetime.now(timezone.utc)
    row = CurriculumVitae(
        id=cv_id,
        user_id=user.id,
        template_id=body.templateId or "atlas",
        title=body.title or "Mon CV",
        principal=bool(body.principal),
        completion=completion,
        payload=data,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.add(
        Notification(
            user_id=user.id,
            type="cv",
            kind="cv",
            message=f"CV « {row.title} » créé.",
            href=f"/cv/{row.id}",
            actor="Nogalix",
        )
    )
    db.commit()
    db.refresh(row)
    return _serialize(row)


def update_cv(db: Session, user: User, cv_id: str, body: CvPayload) -> dict:
    from app.modules.plans.capability import ensure_can_use_template

    row = (
        db.query(CurriculumVitae)
        .filter(CurriculumVitae.id == cv_id, CurriculumVitae.user_id == user.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail={"message": "CV introuvable."})

    ensure_can_use_template(db, user, body.templateId or row.template_id)

    data = body.model_dump(exclude_none=False)
    data["id"] = cv_id

    if body.principal:
        db.query(CurriculumVitae).filter(
            CurriculumVitae.user_id == user.id,
            CurriculumVitae.id != cv_id,
            CurriculumVitae.principal.is_(True),
        ).update({"principal": False})

    row.template_id = body.templateId or row.template_id
    row.title = body.title or row.title
    row.principal = bool(body.principal)
    row.completion = compute_completion(data)
    row.payload = data
    row.updated_at = datetime.now(timezone.utc)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize(row)


def delete_cv(db: Session, user: User, cv_id: str) -> dict:
    row = (
        db.query(CurriculumVitae)
        .filter(CurriculumVitae.id == cv_id, CurriculumVitae.user_id == user.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail={"message": "CV introuvable."})
    db.delete(row)
    db.commit()
    return {"message": "CV supprimé"}


def analyze_cv(db: Session, user: User, cv_id: str) -> dict:
    row = (
        db.query(CurriculumVitae)
        .filter(CurriculumVitae.id == cv_id, CurriculumVitae.user_id == user.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail={"message": "CV introuvable."})

    payload = row.payload or {}
    identity = payload.get("identity") or {}
    experiences = payload.get("experiences") or []
    skills = payload.get("skills") or []
    education = payload.get("education") or []
    summary = (payload.get("summary") or "").strip()

    categories = [
        {
            "id": "identite",
            "label": "Identité",
            "score": 90 if identity.get("firstName") and identity.get("email") else 40,
        },
        {
            "id": "accroche",
            "label": "Accroche",
            "score": 85 if len(summary) >= 80 else 45,
        },
        {
            "id": "experience",
            "label": "Expérience",
            "score": 80 if len(experiences) >= 2 else 50 if experiences else 20,
        },
        {
            "id": "competences",
            "label": "Compétences",
            "score": 85 if len(skills) >= 5 else 55 if skills else 25,
        },
        {
            "id": "formation",
            "label": "Formation",
            "score": 80 if education else 30,
        },
    ]
    score = round(sum(c["score"] for c in categories) / len(categories))
    if score >= 85:
        label = "Très bon"
    elif score >= 70:
        label = "Bon"
    elif score >= 50:
        label = "Moyen"
    else:
        label = "À améliorer"

    suggestions = []
    if len(summary) < 80:
        suggestions.append(
            {
                "id": "summary",
                "title": "Enrichir l'accroche",
                "description": "Rédigez une accroche d'au moins 80 caractères avec votre valeur ajoutée.",
                "impact": "élevé",
            }
        )
    if len(experiences) < 2:
        suggestions.append(
            {
                "id": "xp",
                "title": "Ajouter des expériences",
                "description": "Deux expériences minimum aident les recruteurs à vous évaluer.",
                "impact": "élevé",
            }
        )
    if len(skills) < 5:
        suggestions.append(
            {
                "id": "skills",
                "title": "Compléter les compétences",
                "description": "Listez au moins 5 compétences pertinentes pour votre métier.",
                "impact": "moyen",
            }
        )

    db.add(
        Notification(
            user_id=user.id,
            type="analyse",
            kind="analyse",
            message=f"Analyse du CV « {row.title} » : score {score}/100 ({label}).",
            href="/analyse",
            actor="Nogalix",
        )
    )
    db.commit()

    return {
        "score": score,
        "label": label,
        "suggestions": suggestions,
        "categories": categories,
        "summary": f"Votre CV obtient {score}/100 — {label.lower()}.",
        "cvId": row.id,
    }
