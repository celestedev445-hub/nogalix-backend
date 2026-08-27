from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.modules.users.models import Notification, User

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationIdsRequest(BaseModel):
    notification_ids: list[str] = Field(default_factory=list)


@router.get("")
def index(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (
        db.query(Notification)
        .filter(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )
    unread = [row.to_dict() for row in rows if not row.is_read]
    read = [row.to_dict() for row in rows if row.is_read]
    return {
        "unread_notifications": unread,
        "read_notifications": read,
    }


@router.post("/markAsRead")
def mark_as_read(
    body: NotificationIdsRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not body.notification_ids:
        return {"message": "Aucune notification"}
    now = datetime.now(timezone.utc)
    rows = (
        db.query(Notification)
        .filter(
            Notification.user_id == user.id,
            Notification.id.in_(body.notification_ids),
        )
        .all()
    )
    for row in rows:
        row.is_read = True
        row.read_at = now
        db.add(row)
    db.commit()
    return {"message": "Notifications lues"}


@router.post("/delete")
def delete(
    body: NotificationIdsRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if body.notification_ids:
        db.query(Notification).filter(
            Notification.user_id == user.id,
            Notification.id.in_(body.notification_ids),
        ).delete(synchronize_session=False)
        db.commit()
    return {"message": "Notifications supprimées"}
