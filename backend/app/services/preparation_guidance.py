"""Deterministic, explainable preparation guidance (Phase 5).

No external LLM: ``priority`` is not computed here at all — it is copied
directly from the Phase 4 ``SkillGap.importance`` a plan item is generated
from, since that already applies the exact rule this phase's spec restates
("missing required -> HIGH, missing preferred -> MEDIUM, related -> LOW").
This module supplies the two things Phase 4 did not need: a one-sentence
``reason`` (a fixed template per gap type) and a ``learning_focus`` starting
point (a per-skill lookup, ``app.core.skill_catalog.LEARNING_FOCUS``, with a
generic but still concrete fallback for any skill not in that table).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.skill_catalog import LEARNING_FOCUS
from app.models.enums import JobRequirementType, SkillGapImportance, SkillGapType


@dataclass(frozen=True)
class GeneratedItem:
    skill_id: int
    requirement_type: JobRequirementType
    gap_type: SkillGapType
    priority: SkillGapImportance
    reason: str
    learning_focus: str


def learning_focus_for(skill_name: str) -> str:
    return LEARNING_FOCUS.get(
        skill_name, f"Review core {skill_name} concepts and build a small project that uses it."
    )


def reason_for(
    *,
    gap_type: SkillGapType,
    job_title: str,
    skill_name: str,
    related_to_skill_name: str | None,
) -> str:
    if gap_type == SkillGapType.MISSING_REQUIRED:
        return f'"{job_title}" lists {skill_name} as required, and it was not found in your profile.'
    if gap_type == SkillGapType.MISSING_PREFERRED:
        return f'"{job_title}" lists {skill_name} as preferred, and it was not found in your profile.'
    # RELATED
    if related_to_skill_name:
        return (
            f'"{job_title}" asks for {skill_name}. Your profile shows {related_to_skill_name}, '
            "which is related but does not fully satisfy this requirement."
        )
    return f'"{job_title}" asks for {skill_name}, which a related skill in your profile does not fully satisfy.'
