"""Preparation-plan API contracts (Phase 5)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.enums import (
    JobRequirementType,
    PreparationItemStatus,
    SkillGapImportance,
    SkillGapType,
)


class PreparationItemOut(BaseModel):
    id: int
    skill_id: int
    name: str
    category: str | None
    requirement_type: JobRequirementType
    gap_type: SkillGapType
    priority: SkillGapImportance
    reason: str
    learning_focus: str
    status: PreparationItemStatus


class PreparationItemStatusUpdate(BaseModel):
    status: PreparationItemStatus


class PreparationPlanDetail(BaseModel):
    id: int
    job_profile_id: int
    job_title: str
    match_analysis_id: int
    readiness_score: float

    total_items: int
    completed_items: int
    in_progress_items: int
    not_started_items: int
    progress_percent: float

    items: list[PreparationItemOut]

    created_at: datetime
    updated_at: datetime
