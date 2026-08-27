from fastapi import APIRouter, Request, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.config import settings
from app.core.limiter import limiter

router = APIRouter(tags=["contact"])


class ContactRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    objet: str = Field(min_length=2, max_length=190)
    message: str = Field(min_length=5, max_length=5000)


@router.post("/contact", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
def contact(request: Request, body: ContactRequest):
    # Mail can be wired later; acknowledge for frontend toast.
    _ = settings.contact_to_email
    return {
        "message": "Message reçu. Nous vous répondrons rapidement.",
        "data": {
            "name": body.name,
            "email": str(body.email),
            "objet": body.objet,
        },
    }
