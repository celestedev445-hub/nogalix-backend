from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PlanCreateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    slug: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=120)
    description: Optional[str] = None
    tagline: Optional[str] = None
    price: int = Field(ge=0, default=0)
    duration_months: int = Field(ge=1, le=36, default=1)
    level: int = Field(ge=1, le=10, default=1)
    is_active: bool = True
    highlighted: bool = False
    popular: bool = False
    cta: str = Field(default="Choisir", max_length=80)
    seed_catalog: bool = True


class PlanUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    description: Optional[str] = None
    tagline: Optional[str] = None
    price: Optional[int] = Field(default=None, ge=0)
    duration_months: Optional[int] = Field(default=None, ge=1, le=36)
    level: Optional[int] = Field(default=None, ge=1, le=10)
    is_active: Optional[bool] = None
    highlighted: Optional[bool] = None
    popular: Optional[bool] = None
    cta: Optional[str] = Field(default=None, max_length=80)


class LimitationUpsertRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    key: str = Field(min_length=2, max_length=120)
    limitation_type: str = Field(default="boolean", pattern="^(boolean|count)$")
    value: int = 0
    description: Optional[str] = Field(default=None, max_length=255)


class FeatureUpsertRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=2, max_length=190)
    description: Optional[str] = Field(default=None, max_length=255)
    is_enabled: bool = True
    sort_order: int = 0


class AssignPlanRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    plan_id: int
