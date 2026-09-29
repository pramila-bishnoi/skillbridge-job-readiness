"""Job-comparison API contracts (Phase 7)."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class JobComparisonRequest(BaseModel):
    job_profile_ids: list[int] = Field(min_length=2, max_length=5)

    @field_validator("job_profile_ids")
    @classmethod
    def _no_duplicates(cls, value: list[int]) -> list[int]:
        if len(set(value)) != len(value):
            raise ValueError("job_profile_ids must not repeat the same job")
        return value


class JobComparisonEntry(BaseModel):
    job_profile_id: int
    title: str
    company: str | None
    readiness_score: float
    required_skill_coverage: float
    preferred_skill_coverage: float
    matched_skills: list[str]
    missing_skills: list[str]
    # Missing for this job but not for every job being compared — see
    # services/job_comparison_rules.compare.
    unique_missing_skills: list[str]


class JobComparisonResult(BaseModel):
    jobs: list[JobComparisonEntry]
    common_skills: list[str]
    common_missing_skills: list[str]
