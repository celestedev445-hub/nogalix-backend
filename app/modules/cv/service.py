from datetime import datetime, timezone
import re
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.cv.match_analyse import _cv_to_text, build_match_analysis
from app.modules.cv.rewrite_analyse import _minimal_cv_from_text, build_rewrite_cv
from app.modules.cv.analyse_schemas import CvMatchAnalyseRequest, CvRewriteAnalyseRequest
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


def analyze_cv(db: Session, user: User, cv_id: str, job_offer: str = "") -> dict:
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

    def tokenize(text: str) -> list[str]:
        words = re.findall(r"[a-z0-9+#.]{4,}", text.lower())
        return list(dict.fromkeys(words))

    job_tokens = tokenize(job_offer)[:16] if job_offer.strip() else []
    cv_text = " ".join(
        [
            str(identity.get("firstName") or ""),
            str(identity.get("title") or ""),
            summary,
            " ".join(str(skill.get("name") or "") for skill in skills),
            " ".join(
                " ".join(
                    [
                        str(item.get("title") or ""),
                        str(item.get("company") or ""),
                        " ".join(item.get("bullets") or []),
                    ]
                )
                for item in experiences
            ),
        ]
    )
    cv_tokens = set(tokenize(cv_text))
    keywords_found = [word for word in job_tokens if word in cv_tokens]
    keywords_missing = [word for word in job_tokens if word not in cv_tokens][:8]

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
        "summary": f"Votre CV obtient {score}/100 : {label.lower()}.",
        "cvId": row.id,
        "keywordsFound": keywords_found,
        "keywordsMissing": keywords_missing,
    }


async def match_analyse(db: Session, user: User, body: CvMatchAnalyseRequest) -> dict:
    cv_label = body.fileName or "CV importé"
    cv_text = (body.resumeText or "").strip()
    cv_id = body.cvId

    if cv_id:
        row = (
            db.query(CurriculumVitae)
            .filter(CurriculumVitae.id == cv_id, CurriculumVitae.user_id == user.id)
            .first()
        )
        if not row:
            raise HTTPException(status_code=404, detail={"message": "CV introuvable."})
        payload = row.payload or {}
        cv_label = row.title or cv_label
        cv_text = _cv_to_text(payload)

    if len(cv_text) < 40:
        raise HTTPException(
            status_code=422,
            detail={"message": "Le CV ne contient pas assez d'informations pour une comparaison fiable."},
        )

    result = await build_match_analysis(
        cv_label=cv_label,
        cv_text=cv_text,
        job_offer=body.jobOffer.strip(),
        cv_id=cv_id,
    )

    db.add(
        Notification(
            user_id=user.id,
            type="analyse",
            kind="analyse",
            message=(
                f"Comparaison CV / offre : {result.get('verdictLabel', 'Analyse')} "
                f"({result.get('matchScore', 0)}/100)."
            ),
            href="/analyse",
            actor="Nogalix",
        )
    )
    db.commit()
    return result


async def rewrite_from_analyse(db: Session, user: User, body: CvRewriteAnalyseRequest) -> dict:
    cv_source: dict = {}
    cv_text = (body.resumeText or "").strip()
    job_title = body.jobTitle or ""

    if body.cvId:
        row = (
            db.query(CurriculumVitae)
            .filter(CurriculumVitae.id == body.cvId, CurriculumVitae.user_id == user.id)
            .first()
        )
        if not row:
            raise HTTPException(status_code=404, detail={"message": "CV introuvable."})
        cv_source = dict(row.payload or {})
        cv_text = _cv_to_text(cv_source)

    if not cv_source and cv_text:
        cv_source = _minimal_cv_from_text(cv_text, body.fileName or "CV importé")

    if not cv_text or len(cv_text) < 40:
        raise HTTPException(
            status_code=422,
            detail={"message": "Le CV ne contient pas assez d'informations pour une réécriture fiable."},
        )

    actions = [{"title": a.title, "detail": a.detail} for a in body.actions]
    result = await build_rewrite_cv(
        cv=cv_source,
        cv_text=cv_text,
        job_offer=body.jobOffer.strip(),
        template_id=body.templateId,
        actions=actions,
        job_title=job_title or None,
        file_name=body.fileName or "CV importé",
    )
    return result
