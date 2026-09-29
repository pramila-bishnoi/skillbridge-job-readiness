"""Job-readiness analysis API contracts (Phase 4)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.enums import JobRequirementType, SkillGapImportance, SkillGapType


class SkillGapOut(BaseModel):
    """One row of the skill-by-skill breakdown behind an analysis — backs all
    three read views (matched / missing / gaps), just filtered differently."""

    skill_id: int
    name: str
    category: str | None
    requirement_type: JobRequirementType
    gap_type: SkillGapType
    importance: SkillGapImportance
    evidence: str
    related_to_skill_name: str | None = None


class MatchAnalysisDetail(BaseModel):
    id: int
    job_profile_id: int
    job_title: str

    readiness_score: float
    score_version: str

    required_skill_coverage: float
    required_matched_count: int
    required_total_count: int

    preferred_skill_coverage: float
    preferred_matched_count: int
    preferred_total_count: int

    experience_score: float
    experience_evidence: str

    text_similarity_score: float
    text_similarity_terms: str | None

    matched_skills: list[SkillGapOut]
    missing_skills: list[SkillGapOut]
    skill_gaps: list[SkillGapOut]

    created_at: datetime
    updated_at: datetime
