"""Student profile and resume API contracts."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.skill import StudentSkillOut


class StudentProfileCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    education: str | None = Field(default=None, max_length=4000)
    skills: str | None = Field(default=None, max_length=4000)
    projects: str | None = Field(default=None, max_length=8000)
    experience: str | None = Field(default=None, max_length=8000)


class StudentProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    education: str | None = Field(default=None, max_length=4000)
    skills: str | None = Field(default=None, max_length=4000)
    projects: str | None = Field(default=None, max_length=8000)
    experience: str | None = Field(default=None, max_length=8000)


class StudentProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    education: str | None
    skills: str | None
    projects: str | None
    experience: str | None
    resume_uploaded: bool
    resume_filename: str | None
    # Canonical, normalized skills (Phase 2) — no longer the raw Phase 1
    # JSON list of skill name strings.
    extracted_skills: list[StudentSkillOut]
    created_at: datetime
    updated_at: datetime


class StudentProfileCreatedResponse(BaseModel):
    profile: StudentProfileResponse
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
