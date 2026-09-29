"""Normalized skill API contracts."""

from __future__ import annotations

from pydantic import BaseModel

from app.models.enums import SkillMatchType


class StudentSkillOut(BaseModel):
    """One canonical skill a student's resume evidenced.

    ``matched_text`` and ``match_type`` are kept alongside the canonical
    ``name`` so the UI (and the student) can see *why* the skill was detected,
    not just that it was — required by the SkillBridge explainability rule.
    """

    skill_id: int
    name: str
    category: str | None
    matched_text: str
    match_type: SkillMatchType
