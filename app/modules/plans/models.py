from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tagline: Mapped[Optional[str]] = mapped_column(String(190), nullable=True)
    price: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_months: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    highlighted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    popular: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cta: Mapped[str] = mapped_column(String(80), nullable=False, default="Choisir")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    limitations: Mapped[list["PlanLimitation"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan", order_by="PlanLimitation.key"
    )
    features: Mapped[list["PlanFeature"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan", order_by="PlanFeature.sort_order"
    )

    def to_dict(self, *, include_children: bool = True) -> dict:
        payload = {
            "id": self.id,
            "slug": self.slug,
            "name": self.name,
            "description": self.description,
            "tagline": self.tagline,
            "price": self.price,
            "priceMonthly": self.price,
            "duration_months": self.duration_months,
            "level": self.level,
            "is_active": bool(self.is_active),
            "highlighted": bool(self.highlighted),
            "popular": bool(self.popular),
            "cta": self.cta,
        }
        if include_children:
            payload["limitations"] = [item.to_dict() for item in self.limitations]
            payload["features"] = [item.to_dict() for item in self.features]
            payload["feature_names"] = [
                item.name for item in self.features if item.is_enabled
            ]
        return payload


class PlanLimitation(Base):
    __tablename__ = "plan_limitations"
    __table_args__ = (UniqueConstraint("plan_id", "key", name="uq_plan_limitation_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    limitation_type: Mapped[str] = mapped_column(String(30), nullable=False, default="boolean")
    value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    plan: Mapped["Plan"] = relationship(back_populates="limitations")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "plan_id": self.plan_id,
            "key": self.key,
            "limitation_type": self.limitation_type,
            "value": self.value,
            "description": self.description,
        }


class PlanFeature(Base):
    __tablename__ = "plan_features"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(190), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    plan: Mapped["Plan"] = relationship(back_populates="features")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "plan_id": self.plan_id,
            "name": self.name,
            "description": self.description,
            "is_enabled": bool(self.is_enabled),
            "sort_order": self.sort_order,
        }
