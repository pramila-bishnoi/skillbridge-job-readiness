"""``match_analyses`` — an explainable job-readiness analysis for one
(student, job) pair.

Phase 4. One row per ``(student_profile_id, job_profile_id)`` pair — a rerun
(``services/readiness.ReadinessService.analyze``) recomputes and overwrites
the existing row in place rather than inserting a new one, the same
replace-not-accumulate pattern Phase 2/3 use for skill evidence. That is what
"avoid creating duplicate active analyses" means here: the unique constraint
below makes a duplicate impossible, and "the latest analysis" is simply the
one row that exists.

Every component the final ``readiness_score`` is built from is its own
column, so the API and UI can show *why* the score is what it is instead of
just the number — see ``services/readiness_scoring.py`` for the formula.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.job_profile import JobProfile
    from app.models.skill_gap import SkillGap
    from app.models.student_profile import StudentProfile


class MatchAnalysis(Base, TimestampMixin):
    __tablename__ = "match_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_profile_id: Mapped[int] = mapped_column(
        ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_profile_id: Mapped[int] = mapped_column(
        ForeignKey("job_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # ---- components (each 0-100, independently inspectable) --------------
    required_skill_coverage: Mapped[float] = mapped_column(Float, nullable=False)
    required_matched_count: Mapped[int] = mapped_column(Integer, nullable=False)
    required_total_count: Mapped[int] = mapped_column(Integer, nullable=False)

    preferred_skill_coverage: Mapped[float] = mapped_column(Float, nullable=False)
    preferred_matched_count: Mapped[int] = mapped_column(Integer, nullable=False)
    preferred_total_count: Mapped[int] = mapped_column(Integer, nullable=False)

    experience_score: Mapped[float] = mapped_column(Float, nullable=False)
    # Human-readable sentence explaining experience_score, e.g. "Detected 2
    # year(s) ... against a 3-5 years requirement." Never blank.
    experience_evidence: Mapped[str] = mapped_column(String(300), nullable=False)

    # Reuses services/matching.score_pair (the legacy ATS's own TF-IDF/cosine
    # engine) as ONE input among several — never the sole readiness signal.
    text_similarity_score: Mapped[float] = mapped_column(Float, nullable=False)
    text_similarity_terms: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # ---- final ------------------------------------------------------------
    readiness_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    # Weights/formula live in services/readiness_scoring.py; bumping this
    # string is how a future change to that formula would be surfaced to a
    # client without silently reinterpreting an old stored score.
    score_version: Mapped[str] = mapped_column(String(20), nullable=False, default="v1")

    student_profile: Mapped[StudentProfile] = relationship()
    job_profile: Mapped[JobProfile] = relationship()
    skill_gaps: Mapped[list[SkillGap]] = relationship(
        back_populates="match_analysis", cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (
        Index(
            "uq_match_analyses_student_job", "student_profile_id", "job_profile_id", unique=True
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<MatchAnalysis student={self.student_profile_id} job={self.job_profile_id} score={self.readiness_score}>"
