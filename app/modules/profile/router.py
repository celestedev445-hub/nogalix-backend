from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import hash_password, verify_password
from app.modules.profile.schemas import ChangePasswordRequest, ProfileUpdateRequest
from app.modules.users.models import PersonalAccessToken, User
from app.support.cloudinary_storage import cloudinary_storage

router = APIRouter(prefix="/profile", tags=["profile"])

ALLOWED_AVATAR = {"image/jpeg", "image/png", "image/webp", "image/jpg"}
MAX_AVATAR_BYTES = 5 * 1024 * 1024


@router.get("")
def show(user: User = Depends(get_current_user)):
    payload = user.to_auth_dict()
    return {"data": payload, **payload}


@router.put("")
def update(
    body: ProfileUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    email_norm = str(body.email).lower().strip()
    existing = (
        db.query(User)
        .filter(User.email == email_norm, User.id != user.id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Cet email est déjà utilisé.",
                "errors": {"email": ["Cet email est déjà utilisé."]},
            },
        )

    user.name = body.name.strip()
    user.email = email_norm
    user.phone = body.phone
    user.location = body.location
    db.add(user)
    db.commit()
    db.refresh(user)
    payload = user.to_auth_dict()
    return {"message": "Profil mis à jour", "data": payload, "user": payload}


@router.post("/password")
def change_password(
    body: ChangePasswordRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Ce compte n'a pas encore de mot de passe. Utilisez « Mot de passe oublié » pour en créer un.",
                "code": "no_password",
            },
        )
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Mot de passe actuel incorrect.",
                "code": "invalid_current_password",
            },
        )

    user.password_hash = hash_password(body.password)
    db.add(user)
    db.query(PersonalAccessToken).filter(PersonalAccessToken.user_id == user.id).delete()
    db.commit()
    return {"message": "Mot de passe mis à jour. Reconnectez-vous."}


@router.post("/avatar")
async def avatar(
    avatar: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    content_type = (avatar.content_type or "").lower()
    if content_type not in ALLOWED_AVATAR:
        raise HTTPException(
            status_code=422,
            detail={"message": "Format d'image non supporté (jpeg, png, webp)."},
        )

    raw = await avatar.read()
    if len(raw) > MAX_AVATAR_BYTES:
        raise HTTPException(
            status_code=422,
            detail={"message": "L'avatar ne doit pas dépasser 5 Mo."},
        )
    await avatar.seek(0)

    if user.avatar:
        cloudinary_storage.delete(user.avatar, resource_type="image")

    url = await cloudinary_storage.upload(avatar, folder="avatars", resource_type="image")
    user.avatar = url
    db.add(user)
    db.commit()
    db.refresh(user)
    payload = user.to_auth_dict()
    return {"message": "Avatar mis à jour", "data": payload, "avatar": url, "user": payload}
