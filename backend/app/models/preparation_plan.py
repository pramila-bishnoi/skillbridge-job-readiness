"""``preparation_plans`` — one deterministic preparation plan per (student, readiness analysis).

Phase 5. Anchored to ``match_analysis_id`` rather than ``job_profile_id``
directly, mirroring how ``SkillGap`` anchors to its parent analysis (§10.5):
the plan is generated *from* one readiness analysis's ``SkillGap`` rows, and
because ``MatchAnalysis`` is itself one upserted-in-place row per
(student, job) (Phase 4), its id is stable across readiness reruns — so the
unique constraint below is what makes "regenerate without creating duplicate
active plans" true by construction, exactly like Phase 4's own analyses.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.match_analysis import MatchAnalysis
    from app.models.preparation_item import PreparationItem
    from app.models.student_profile import StudentProfile


class PreparationPlan(Base, TimestampMixin):
    __tablename__ = "preparation_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_profile_id: Mapped[int] = mapped_column(
        ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    match_analysis_id: Mapped[int] = mapped_column(
        ForeignKey("match_analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )

    student_profile: Mapped[StudentProfile] = relationship()
    match_analysis: Mapped[MatchAnalysis] = relationship()
    items: Mapped[list[PreparationItem]] = relationship(
        back_populates="plan", cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (
        Index(
            "uq_preparation_plans_student_analysis",
            "student_profile_id",
            "match_analysis_id",
            unique=True,
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<PreparationPlan student={self.student_profile_id} analysis={self.match_analysis_id}>"
