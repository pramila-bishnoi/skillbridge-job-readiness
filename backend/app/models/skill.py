"""``skills``/``skill_aliases`` tables — the canonical skill catalog.

Phase 2 replaces the Phase 1 hardcoded skill list with data: a canonical
``Skill`` row plus zero or more ``SkillAlias`` rows that resolve a resume
synonym ("Postgres", "ReactJS") back to one canonical skill. Adding a synonym
is then a seed-data change (``app/core/skill_catalog.py``), not a code change.
"""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Skill(Base, TimestampMixin):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Lower-cased, whitespace-collapsed form of ``name`` — keeps "PostgreSQL"
    # from being seeded twice under a different casing.
    normalized_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    # Free text, like jobs.department: a curated but unconstrained vocabulary.
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    aliases: Mapped[list[SkillAlias]] = relationship(
        back_populates="skill", cascade="all, delete-orphan", passive_deletes=True
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Skill {self.name!r}>"


class SkillAlias(Base, TimestampMixin):
    __tablename__ = "skill_aliases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # The synonym exactly as seeded (e.g. "Postgres", "ReactJS") — what
    # normalization matches against, case-insensitively.
    alias: Mapped[str] = mapped_column(String(100), nullable=False)
    normalized_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    skill: Mapped[Skill] = relationship(back_populates="aliases")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<SkillAlias {self.alias!r} -> skill_id={self.skill_id}>"
