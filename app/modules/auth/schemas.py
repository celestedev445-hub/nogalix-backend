from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    password_confirmation: str = Field(min_length=6, max_length=128)

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.password_confirmation:
            raise ValueError("Les mots de passe ne correspondent pas.")
        return self


class GoogleAuthRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    code: Optional[str] = None
    id_token: Optional[str] = None
    credential: Optional[str] = None
    access_token: Optional[str] = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)
    password: str = Field(min_length=6, max_length=128)
    password_confirmation: str = Field(min_length=6, max_length=128)

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.password_confirmation:
            raise ValueError("Les mots de passe ne correspondent pas.")
        return self


class AuthUserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone: Optional[str] = None
    location: Optional[str] = None
    avatar: Optional[str] = None
    has_google: bool = False
    notifyEmail: bool = True
    notifyJobs: bool = True
    notifyAnalysis: bool = True
