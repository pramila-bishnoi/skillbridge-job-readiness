"""``interview_topics`` — one row per generating signal behind an interview
prep set (a job skill the student matched or is missing, one project line
quoted from their profile, or a generic role prompt).

Phase 6. Linked to ``student_profiles``, ``job_profiles`` and
``match_analyses`` explicitly — the same "store it even though it is
technically derivable" choice ``MatchAnalysis`` and ``PreparationPlan``
already made, so every query can filter directly without a join chain.

Unlike ``PreparationPlan``/``MatchAnalysis``, there is no unique constraint
here: a (student, job) pair naturally produces several topics (one per
skill/project/role prompt), so the "one row per pair" invariant those
tables enforce does not apply at the topic level. Regeneration instead
deletes every existing topic for the pair and reinserts fresh ones —
``InterviewTopicRepository.replace_for_job`` — carrying a completed
question's status forward only when the newly generated question text is
byte-identical to before (see that method's docstring for why).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import InterviewCategory

if TYPE_CHECKING:
    from app.models.interview_question import InterviewQuestion
    from app.models.job_profile import JobProfile
    from app.models.match_analysis import MatchAnalysis
    from app.models.skill import Skill
    from app.models.student_profile import StudentProfile


class InterviewTopic(Base, TimestampMixin):
    __tablename__ = "interview_topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_profile_id: Mapped[int] = mapped_column(
        ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_profile_id: Mapped[int] = mapped_column(
        ForeignKey("job_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    match_analysis_id: Mapped[int] = mapped_column(
        ForeignKey("match_analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )

    category: Mapped[InterviewCategory] = mapped_column(
        Enum(
            InterviewCategory,
            native_enum=False,
            length=20,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    # Null for RESUME_PROJECT (tied to a project line, not a catalog skill)
    # and ROLE_CONCEPT (a generic, job-title-only prompt) topics.
    skill_id: Mapped[int | None] = mapped_column(
        ForeignKey("skills.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # For RESUME_PROJECT topics only: the exact line quoted from the
    # student's own ``projects`` text — never a paraphrase or an inference.
    source_evidence: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reason: Mapped[str] = mapped_column(String(300), nullable=False)

    student_profile: Mapped[StudentProfile] = relationship()
    job_profile: Mapped[JobProfile] = relationship()
    match_analysis: Mapped[MatchAnalysis] = relationship()
    skill: Mapped[Skill | None] = relationship()
    questions: Mapped[list[InterviewQuestion]] = relationship(
        back_populates="topic", cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (
        Index("ix_interview_topics_student_job", "student_profile_id", "job_profile_id"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<InterviewTopic job={self.job_profile_id} category={self.category}>"
