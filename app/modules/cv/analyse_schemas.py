from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class CvAnalyseRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    jobOffer: str = ""


class CvUploadAnalyseRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    fileName: str
    contentBase64: str
    jobOffer: str = ""


class CvMatchAnalyseRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    jobOffer: str = Field(min_length=40, max_length=12000)
    cvId: Optional[str] = None
    resumeText: Optional[str] = Field(default=None, max_length=20000)
    fileName: Optional[str] = Field(default=None, max_length=255)


class MatchAction(BaseModel):
    title: str
    detail: str


class CvMatchAnalyseResponse(BaseModel):
    matchScore: int
    verdict: Literal["forte", "partielle", "faible"]
    verdictLabel: str
    summary: str
    alignedPoints: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    actions: list[MatchAction] = Field(default_factory=list)
    source: Literal["ai", "local"] = "local"
    cvLabel: str = "CV"
    jobTitle: Optional[str] = None
    cvId: Optional[str] = None


class CvRewriteAnalyseRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    jobOffer: str = Field(min_length=40, max_length=12000)
    templateId: str = Field(default="atlas", min_length=2, max_length=64)
    cvId: Optional[str] = None
    resumeText: Optional[str] = Field(default=None, max_length=20000)
    fileName: Optional[str] = Field(default=None, max_length=255)
    jobTitle: Optional[str] = Field(default=None, max_length=120)
    actions: list[MatchAction] = Field(default_factory=list)


class CvRewriteAnalyseResponse(BaseModel):
    payload: dict[str, Any]
    source: Literal["ai", "local"] = "local"


class AnalysisSuggestion(BaseModel):
    id: str
    title: str
    description: str
    impact: Literal["élevé", "moyen", "faible"] = "moyen"


class AnalysisCategory(BaseModel):
    id: str
    label: str
    score: int


class CvAnalyseResponse(BaseModel):
    score: int
    label: str
    summary: str
    suggestions: list[AnalysisSuggestion] = Field(default_factory=list)
    categories: list[AnalysisCategory] = Field(default_factory=list)
    cvId: Optional[str] = None
