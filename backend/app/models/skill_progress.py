"""``skill_progress`` — a student's own self-reported progress on one
canonical skill.

Phase 7. Deliberately sparse: a row exists only once a student has explicitly
set a status for that skill via ``PATCH .../skill-progress/{skill_id}`` — it
is not auto-created for every resume-extracted or job-required skill, since
most students will only ever care about tracking a handful. One row per
(student, skill) — ``updated_at`` (``TimestampMixin``) is the "last updated"
timestamp the task asks for, maintained by the database on every write, not
by application code.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import SkillProgressStatus

if TYPE_CHECKING:
    from app.models.skill import Skill
    from app.models.student_profile import StudentProfile


class SkillProgress(Base, TimestampMixin):
    __tablename__ = "skill_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_profile_id: Mapped[int] = mapped_column(
        ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[SkillProgressStatus] = mapped_column(
        Enum(
            SkillProgressStatus,
            native_enum=False,
            length=20,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )

    student_profile: Mapped[StudentProfile] = relationship()
    skill: Mapped[Skill] = relationship()

    __table_args__ = (
        Index("uq_skill_progress_student_skill", "student_profile_id", "skill_id", unique=True),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<SkillProgress student={self.student_profile_id} skill={self.skill_id} status={self.status}>"
