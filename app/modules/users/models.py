from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(190), unique=True, nullable=False, index=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reset_code: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reset_code_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(190), nullable=True)
    avatar: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    google_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, unique=True)
    has_google: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)
    role: Mapped[str] = mapped_column(String(30), default="user", nullable=False, index=True)
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notify_email: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_jobs: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_analysis: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    plan_id: Mapped[Optional[int]] = mapped_column(ForeignKey("plans.id", ondelete="SET NULL"), nullable=True, index=True)
    ai_trials_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ai_trials_period: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    tokens: Mapped[list["PersonalAccessToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    cvs: Mapped[list["CurriculumVitae"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def is_admin(self) -> bool:
        return (self.role or "").strip().lower() == "admin"

    def to_auth_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "location": self.location,
            "avatar": self.avatar,
            "has_google": bool(self.has_google),
            "role": self.role or "user",
            "is_admin": self.is_admin(),
            "plan_id": self.plan_id,
            "notifyEmail": bool(self.notify_email),
            "notifyJobs": bool(self.notify_jobs),
            "notifyAnalysis": bool(self.notify_analysis),
        }


class PersonalAccessToken(Base):
    __tablename__ = "personal_access_tokens"
    __table_args__ = (UniqueConstraint("token_hash", name="uq_pat_token_hash"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80), default="authToken", nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    abilities: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    user: Mapped[User] = relationship(back_populates="tokens")

    @property
    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return expires < utcnow()

    def touch(self) -> None:
        self.last_used_at = utcnow()


class CurriculumVitae(Base):
    __tablename__ = "cvs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    template_id: Mapped[str] = mapped_column(String(80), nullable=False, default="atlas")
    title: Mapped[str] = mapped_column(String(190), nullable=False, default="Mon CV")
    principal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    completion: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    user: Mapped[User] = relationship(back_populates="cvs")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(80), nullable=False, default="systeme")
    kind: Mapped[str] = mapped_column(String(40), nullable=False, default="systeme")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    href: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    actor: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    user: Mapped[User] = relationship(back_populates="notifications")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "kind": self.kind,
            "message": self.message,
            "href": self.href,
            "is_read": self.is_read,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "actor": self.actor,
        }
