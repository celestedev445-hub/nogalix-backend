from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


ALLOWED_STATUS = ("en attente", "en traitement", "résolu")
ALLOWED_SUJETS = ("bug", "feature", "question", "other")


class SupportCreateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    nom: str = Field(min_length=1, max_length=255)
    email: EmailStr
    sujet: str = Field(min_length=1, max_length=80)
    message: str = Field(min_length=10, max_length=8000)


class SupportUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    nom: Optional[str] = Field(default=None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    sujet: Optional[str] = Field(default=None, min_length=1, max_length=80)
    message: Optional[str] = Field(default=None, min_length=10, max_length=8000)
    status: Optional[str] = None


class SupportReplyRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    message: str = Field(min_length=2, max_length=5000)
