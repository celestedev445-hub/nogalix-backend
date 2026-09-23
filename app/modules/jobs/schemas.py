from pydantic import BaseModel, ConfigDict, Field


class JobMatchCv(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str = ""
    jobTitle: str = ""
    summary: str = ""
    skills: list[str] = Field(default_factory=list)
    experiences: list[str] = Field(default_factory=list)


class JobMatchItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    title: str = ""
    company: str = ""
    tags: list[str] = Field(default_factory=list)
    summary: str = ""


class JobMatchRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    cv: JobMatchCv
    jobs: list[JobMatchItem] = Field(default_factory=list, max_length=40)
