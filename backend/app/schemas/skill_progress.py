"""Skill-progress API contracts (Phase 7)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.enums import SkillProgressStatus


class SkillProgressUpdate(BaseModel):
    status: SkillProgressStatus


class SkillProgressOut(BaseModel):
    skill_id: int
    name: str
    category: str | None
    status: SkillProgressStatus
    updated_at: datetime


class SkillCatalogEntry(BaseModel):
    """A thin read of the Phase 2 catalog, so the UI can offer a skill to
    track progress on even when it isn't (yet) on the student's resume."""

    skill_id: int
    name: str
    category: str | None
