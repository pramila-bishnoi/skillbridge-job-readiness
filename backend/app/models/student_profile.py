"""Student-owned profile and resume intelligence foundation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.job_profile import JobProfile
    from app.models.student_skill import StudentSkill


class StudentProfile(Base, TimestampMixin):
    __tablename__ = "student_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    education: Mapped[str | None] = mapped_column(Text, nullable=True)
    skills: Mapped[str | None] = mapped_column(Text, nullable=True)
    projects: Mapped[str | None] = mapped_column(Text, nullable=True)
    experience: Mapped[str | None] = mapped_column(Text, nullable=True)

    resume_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    resume_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resume_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Phase 1 leftover: a JSON-encoded flat list of skill names. Superseded by
    # the ``student_skills`` relationship below (Phase 2) and no longer
    # written to, but the column stays — migrations are additive only
    # (CLAUDE.md §7, "Alembic is the schema").
    extracted_skills: Mapped[str | None] = mapped_column(Text, nullable=True)
    resume_uploaded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    normalized_skills: Mapped[list[StudentSkill]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", passive_deletes=True
    )
    job_profiles: Mapped[list[JobProfile]] = relationship(
        back_populates="student_profile", cascade="all, delete-orphan", passive_deletes=True
    )
