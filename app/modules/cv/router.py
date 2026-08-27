from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.modules.cv import service as cv_service
from app.modules.cv.schemas import CvPayload
from app.modules.users.models import User

router = APIRouter(prefix="/cv", tags=["cv"])


@router.get("")
def index(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return cv_service.list_cvs(db, user)


@router.get("/{cv_id}")
def show(cv_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return cv_service.get_cv(db, user, cv_id)


@router.post("")
def store(body: CvPayload, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return cv_service.create_cv(db, user, body)


@router.put("/{cv_id}")
def update(
    cv_id: str,
    body: CvPayload,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return cv_service.update_cv(db, user, cv_id, body)


@router.delete("/{cv_id}")
def destroy(cv_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return cv_service.delete_cv(db, user, cv_id)


@router.post("/{cv_id}/analyse")
def analyse(cv_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return cv_service.analyze_cv(db, user, cv_id)
