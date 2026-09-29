"""Job-URL-import API contracts ("Import from Job URL" on Analyze a Job)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.job_profile import JobRequirementSkillOut


class JobUrlImportRequest(BaseModel):
    url: str = Field(min_length=8, max_length=2048)


class JobUrlImportPreviewOut(BaseModel):
    source_url: str
    extraction_method: str
    title: str | None
    company: str | None
    location: str | None
    employment_type: str | None
    compensation: str | None
    posted_date: str | None
    description: str
    experience_required: str | None
    experience_evidence: str | None
    required_skills: list[JobRequirementSkillOut]
    preferred_skills: list[JobRequirementSkillOut]
    warnings: list[str]
