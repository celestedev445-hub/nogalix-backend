from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class CvIdentity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    firstName: str = ""
    lastName: str = ""
    title: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    photo: Optional[str] = None
    website: Optional[str] = None
    github: Optional[str] = None


class ExperienceItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    title: str = ""
    company: str = ""
    location: Optional[str] = None
    start: str = ""
    end: str = ""
    current: Optional[bool] = False
    bullets: list[str] = Field(default_factory=list)


class EducationItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    diploma: str = ""
    school: str = ""
    year: str = ""
    details: Optional[str] = None


class SkillItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    name: str = ""
    level: int = 0


class LanguageItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    name: str = ""
    level: str = ""


class ProjectItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    name: str = ""
    description: str = ""
    url: Optional[str] = None


class CertificationItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    name: str = ""
    issuer: str = ""
    year: str = ""


class InterestItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    name: str = ""


class CvImportSource(BaseModel):
    model_config = ConfigDict(extra="ignore")

    fileName: str = ""
    mimeType: str = ""
    dataUrl: str = ""


class CvPayload(BaseModel):
    """Matches frontend CvData — templates stay on frontend via templateId."""

    model_config = ConfigDict(extra="ignore")

    id: Optional[str] = None
    templateId: str = "atlas"
    title: str = "Mon CV"
    principal: Optional[bool] = False
    editorStatus: Literal["draft", "ready"] = "draft"
    updatedAt: Optional[str] = None
    completion: int = 0
    identity: CvIdentity = Field(default_factory=CvIdentity)
    summary: str = ""
    experiences: list[ExperienceItem] = Field(default_factory=list)
    education: list[EducationItem] = Field(default_factory=list)
    skills: list[SkillItem] = Field(default_factory=list)
    languages: list[LanguageItem] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)
    certifications: list[CertificationItem] = Field(default_factory=list)
    interests: Optional[list[InterestItem]] = None
    importSource: Optional[CvImportSource] = None


def compute_completion(payload: dict[str, Any]) -> int:
    identity = payload.get("identity") or {}
    score = 0
    if identity.get("firstName") and identity.get("lastName"):
        score += 15
    if identity.get("email"):
        score += 10
    if identity.get("title"):
        score += 10
    if (payload.get("summary") or "").strip():
        score += 15
    if payload.get("experiences"):
        score += 20
    if payload.get("education"):
        score += 10
    if payload.get("skills"):
        score += 10
    if payload.get("languages"):
        score += 5
    if payload.get("templateId"):
        score += 5
    return min(100, score)
