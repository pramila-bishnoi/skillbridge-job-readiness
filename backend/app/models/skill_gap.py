"""``skill_gaps`` — the per-skill breakdown behind one ``MatchAnalysis``.

Phase 4. One row per job skill (required or preferred) considered by an
analysis, covering all four ``SkillGapType`` values — including ``MATCHED``
— so this single table backs all three read views the API exposes: matched
skills, missing skills, and prioritized skill gaps (``services/readiness.py``
filters the same rows three ways rather than maintaining three tables).

Anchored to ``match_analysis_id`` alone rather than also duplicating
``student_profile_id``/``job_profile_id`` here: the parent analysis already
carries both, matching ``docs/SKILLBRIDGE_ARCHITECTURE.md`` §10.5
("``skill_gaps``: analysis ID and requirement/skill reference").
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import JobRequirementType, SkillGapImportance, SkillGapType

if TYPE_CHECKING:
    from app.models.match_analysis import MatchAnalysis
    from app.models.skill import Skill


class SkillGap(Base, TimestampMixin):
    __tablename__ = "skill_gaps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_analysis_id: Mapped[int] = mapped_column(
        ForeignKey("match_analyses.id", ondelete="CASCADE"), nullable=False, index=True
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
    importance: Mapped[SkillGapImportance] = mapped_column(
        Enum(
            SkillGapImportance,
            native_enum=False,
            length=10,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    # Always populated — "Found in your normalized skills.",
    # "Not found ...; the job lists this as required.", etc. Never blank, so
    # the UI never has to fall back to an unexplained badge.
    evidence: Mapped[str] = mapped_column(String(300), nullable=False)
    # Only set for gap_type == RELATED: which of the student's OWN skills the
    # relationship was found against (app.models.skill_relation.SkillRelation).
    related_to_skill_id: Mapped[int | None] = mapped_column(
        ForeignKey("skills.id", ondelete="SET NULL"), nullable=True
    )

    match_analysis: Mapped[MatchAnalysis] = relationship(back_populates="skill_gaps")
    skill: Mapped[Skill] = relationship(foreign_keys=[skill_id])
    related_to_skill: Mapped[Skill | None] = relationship(foreign_keys=[related_to_skill_id])

    __table_args__ = (
        Index("uq_skill_gaps_analysis_skill", "match_analysis_id", "skill_id", unique=True),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<SkillGap analysis={self.match_analysis_id} skill={self.skill_id} type={self.gap_type}>"
