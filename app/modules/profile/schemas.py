from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class ProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: Optional[str] = Field(default=None, max_length=40)
    location: Optional[str] = Field(default=None, max_length=190)


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    current_password: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=6, max_length=128)
    password_confirmation: str = Field(min_length=6, max_length=128)

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.password_confirmation:
            raise ValueError("Les mots de passe ne correspondent pas.")
        return self
