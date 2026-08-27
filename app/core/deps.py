from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import hash_token
from app.modules.users.models import PersonalAccessToken, User


def _extract_bearer(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


def get_current_user(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    token = _extract_bearer(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Non authentifié."},
        )

    token_hash = hash_token(token)
    row = (
        db.query(PersonalAccessToken)
        .filter(PersonalAccessToken.token_hash == token_hash)
        .first()
    )
    if not row or row.is_expired:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Veuillez vous reconnecter."},
        )

    user = db.query(User).filter(User.id == row.user_id).first()
    if not user or user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Compte indisponible."},
        )

    row.touch()
    db.add(row)
    db.commit()
    return user


def get_optional_user(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    token = _extract_bearer(authorization)
    if not token:
        return None
    try:
        return get_current_user(authorization=authorization, db=db)
    except HTTPException:
        return None


def require_admin(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if user.is_admin():
        return user

    # Bootstrap : emails dans ADMIN_EMAILS → promotion role=admin (persistée).
    allowlist = {
        item.strip().lower()
        for item in (settings.admin_emails or "").split(",")
        if item.strip()
    }
    email = (user.email or "").strip().lower()
    if email and email in allowlist:
        user.role = "admin"
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"message": "Accès administrateur requis.", "code": "admin_required"},
    )
