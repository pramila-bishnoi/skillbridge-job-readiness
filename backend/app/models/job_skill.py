"""``job_skills`` — one row per canonical skill a saved job description evidences.

The scoped-down implementation of the ``job_requirements`` table
``docs/SKILLBRIDGE_ARCHITECTURE.md`` §10.4 describes: it only ever holds
skill/technology requirements (``requirement_type`` REQUIRED or PREFERRED),
not the RESPONSIBILITY/EXPERIENCE requirement types that document also
anticipates — experience is extracted separately onto ``JobProfile`` itself.
Reuses ``SkillMatchType`` from Phase 2 rather than inventing a parallel enum,
since "how was this skill identified" means the same thing whether the text
being scanned is a resume or a job description.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import JobRequirementType, SkillMatchType

if TYPE_CHECKING:
    from app.models.job_profile import JobProfile
    from app.models.skill import Skill


class JobSkill(Base, TimestampMixin):
    __tablename__ = "job_skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_profile_id: Mapped[int] = mapped_column(
        ForeignKey("job_profiles.id", ondelete="CASCADE"), nullable=False, index=True
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
    # The exact substring in the job description that triggered the match —
    # same explainability pattern as StudentSkill.matched_text.
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

    job_profile: Mapped[JobProfile] = relationship(back_populates="skills")
    skill: Mapped[Skill] = relationship()

    __table_args__ = (
        # One row per skill per job analysis — required wins over preferred
        # when a skill would otherwise appear in both (see job_analysis.py),
        # so requirement_type is not part of this key.
        Index("uq_job_skills_profile_skill", "job_profile_id", "skill_id", unique=True),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<JobSkill job_profile={self.job_profile_id} skill={self.skill_id} type={self.requirement_type}>"
