"""``preparation_items`` — one deterministic study item per gap skill.

Phase 5. ``priority``/``requirement_type``/``gap_type`` are copied from the
source Phase 4 ``SkillGap`` row at generation time rather than referenced
live: a ``SkillGap`` row is deleted and recreated whenever readiness is
reanalyzed (``SkillGapRepository.replace_for_analysis``), so a live FK to it
would go stale. ``status`` is the one field generation never overwrites —
``PreparationItemRepository.replace_for_plan`` updates every other column on
a regenerate but leaves a student's own progress alone.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import (
    JobRequirementType,
    PreparationItemStatus,
    SkillGapImportance,
    SkillGapType,
)

if TYPE_CHECKING:
    from app.models.preparation_plan import PreparationPlan
    from app.models.skill import Skill


class PreparationItem(Base, TimestampMixin):
    __tablename__ = "preparation_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    preparation_plan_id: Mapped[int] = mapped_column(
        ForeignKey("preparation_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )

    requirement_type: Mapped[JobRequirementType] = mapped_column(
        Enum(
            JobRequirementType,
            native_enum=False,
            length=20,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    gap_type: Mapped[SkillGapType] = mapped_column(
        Enum(
            SkillGapType,
            native_enum=False,
            length=20,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    # Copied directly from SkillGap.importance (Phase 4) — the same
    # deterministic rule, not recomputed: missing-required -> HIGH,
    # missing-preferred -> MEDIUM, related -> LOW.
    priority: Mapped[SkillGapImportance] = mapped_column(
        Enum(
            SkillGapImportance,
            native_enum=False,
            length=10,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    # Always populated — a template sentence naming the job and the skill,
    # e.g. '"Backend Engineer" lists Docker as required, and it was not
    # found in your profile.' See services/preparation_guidance.reason_for.
    reason: Mapped[str] = mapped_column(String(300), nullable=False)
    # A short, concrete starting point, e.g. "containers, images, Dockerfile,
    # and basic deployment." See app.core.skill_catalog.LEARNING_FOCUS.
    learning_focus: Mapped[str] = mapped_column(String(300), nullable=False)

    status: Mapped[PreparationItemStatus] = mapped_column(
        Enum(
            PreparationItemStatus,
            native_enum=False,
            length=20,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=PreparationItemStatus.NOT_STARTED,
    )

    plan: Mapped[PreparationPlan] = relationship(back_populates="items")
    skill: Mapped[Skill] = relationship()

    __table_args__ = (
        Index(
            "uq_preparation_items_plan_skill", "preparation_plan_id", "skill_id", unique=True
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<PreparationItem plan={self.preparation_plan_id} skill={self.skill_id} status={self.status}>"
