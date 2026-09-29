"""``student_skills`` — one row per canonical skill a student's resume evidences.

Kept separate from the free-text ``student_profiles.skills`` column (the
student's own self-reported blurb): this table is derived, normalized
evidence — one row per ``(student_profile, skill)`` — and it is what any
future job-matching/readiness work joins against instead of re-parsing text.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import SkillMatchType

if TYPE_CHECKING:
    from app.models.skill import Skill
    from app.models.student_profile import StudentProfile


class StudentSkill(Base, TimestampMixin):
    __tablename__ = "student_skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_profile_id: Mapped[int] = mapped_column(
        ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # The exact substring that triggered the match, preserved verbatim from
    # the resume text (e.g. "Postgres", "ReactJS") so a student can see *why*
    # a skill was detected, not just that it was.
    matched_text: Mapped[str] = mapped_column(String(200), nullable=False)
    match_type: Mapped[SkillMatchType] = mapped_column(
        Enum(
            SkillMatchType,
            native_enum=False,
            length=20,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )

    profile: Mapped[StudentProfile] = relationship(back_populates="normalized_skills")
    skill: Mapped[Skill] = relationship()

    __table_args__ = (
        # One evidence row per skill per student — a re-upload replaces rows
        # rather than accumulating duplicates (see StudentSkillRepository).
        Index(
            "uq_student_skills_profile_skill",
            "student_profile_id",
            "skill_id",
            unique=True,
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<StudentSkill profile={self.student_profile_id} skill={self.skill_id}>"
