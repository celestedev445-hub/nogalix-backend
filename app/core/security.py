import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt

from app.core.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def generate_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def token_expires_at(minutes: Optional[int] = None) -> datetime:
    ttl = minutes if minutes is not None else settings.auth_token_ttl_minutes
    return datetime.now(timezone.utc) + timedelta(minutes=ttl)
