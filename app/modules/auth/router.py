from typing import Optional

from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.limiter import limiter
from app.modules.auth import service as auth_service
from app.modules.auth.schemas import (
    ForgotPasswordRequest,
    GoogleAuthRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
)
from app.modules.users.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(request: Request, body: RegisterRequest, db: Session = Depends(get_db)):
    return auth_service.register_user(
        db,
        name=body.name,
        email=str(body.email),
        password=body.password,
    )


@router.post("/login")
@limiter.limit("10/minute")
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    return auth_service.login_user(db, email=str(body.email), password=body.password)


@router.post("/forgot-password")
@limiter.limit("5/minute")
def forgot_password(request: Request, body: ForgotPasswordRequest, db: Session = Depends(get_db)):
    return auth_service.forgot_password(db, email=str(body.email))


@router.post("/reset-password")
@limiter.limit("5/minute")
def reset_password(request: Request, body: ResetPasswordRequest, db: Session = Depends(get_db)):
    return auth_service.reset_password(
        db,
        email=str(body.email),
        code=body.code,
        password=body.password,
    )


@router.post("/logout")
def logout(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return auth_service.logout_user(db, authorization)


@router.get("/user")
def me(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from app.modules.plans.capability import capabilities_payload, get_user_plan, plan_summary
    from app.modules.plans.seed import get_default_free_plan
    from app.modules.auth.service import _sync_admin_role

    dirty = False
    if not user.plan_id:
        free = get_default_free_plan(db)
        if free:
            user.plan_id = free.id
            dirty = True
    if _sync_admin_role(user):
        dirty = True
    if dirty:
        db.add(user)
        db.commit()
        db.refresh(user)

    plan = get_user_plan(db, user)
    payload = user.to_auth_dict()
    payload["plan"] = plan_summary(plan)
    payload["capabilities"] = capabilities_payload(plan, user)
    return {"data": payload, "user": payload, **payload}


@router.post("/google")
@limiter.limit("10/minute")
async def google(request: Request, body: GoogleAuthRequest, db: Session = Depends(get_db)):
    return await auth_service.login_with_google(db, body.model_dump(exclude_none=True))
