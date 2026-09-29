"""Saved job-analysis API contracts."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import SkillMatchType


class JobProfileCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    company: str | None = Field(default=None, max_length=150)
    # Bounded so an unreasonably large paste can't dominate request processing
    # time — the analyzer is regex-based, not indexed, so it scans this
    # linearly (docs/SKILLBRIDGE_ARCHITECTURE.md §20, "bound text size").
    description: str = Field(min_length=20, max_length=20000)

    # Populated by the "Import from Job URL" flow (services/job_url_import.py)
    # after the student confirms a preview; every field is optional and null
    # for a manually pasted description, which is still the primary path.
    source_url: str | None = Field(default=None, max_length=2048)
    location: str | None = Field(default=None, max_length=200)
    employment_type: str | None = Field(default=None, max_length=100)
    compensation: str | None = Field(default=None, max_length=200)
    posted_date: str | None = Field(default=None, max_length=100)


class JobRequirementSkillOut(BaseModel):
    """One canonical skill a saved job description evidences, with the same
    matched-text/match-type explainability as a student's own skills."""

    skill_id: int
    name: str
    category: str | None
    matched_text: str
    match_type: SkillMatchType


class JobProfileSummary(BaseModel):
    id: int
    title: str
    company: str | None
    experience_required: str | None
    required_skill_count: int
    preferred_skill_count: int
    created_at: datetime
    updated_at: datetime


class JobProfileDetail(BaseModel):
    id: int
    title: str
    company: str | None
    description: str
    experience_required: str | None
    experience_evidence: str | None
    required_skills: list[JobRequirementSkillOut]
    preferred_skills: list[JobRequirementSkillOut]
    source_url: str | None
    location: str | None
    employment_type: str | None
    compensation: str | None
    posted_date: str | None
    created_at: datetime
    updated_at: datetime
