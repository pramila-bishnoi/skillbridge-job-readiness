"""``skill_relations`` — an explicit, seeded "related to" edge between two skills.

Phase 4 (readiness/skill-gap engine). Deliberately a flat, symmetric table:
each curated pair in ``SKILL_RELATIONSHIPS`` (``app/core/skill_catalog.py``)
is seeded as two rows (A -> B and B -> A) so a lookup by ``skill_id`` alone
finds everything that skill relates to, without an OR-across-two-columns
query. There is no "strength"/confidence column — the relationship either was
curated in or it wasn't; see ``docs/SKILLBRIDGE_ARCHITECTURE.md`` §12.3,
"Related skills should be based on an explicit alias/relationship table ...
not an unexplained fuzzy score."
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.skill import Skill


class SkillRelation(Base, TimestampMixin):
    __tablename__ = "skill_relations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    related_skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )

    skill: Mapped[Skill] = relationship(foreign_keys=[skill_id])
    related_skill: Mapped[Skill] = relationship(foreign_keys=[related_skill_id])

    __table_args__ = (
        Index("uq_skill_relations_pair", "skill_id", "related_skill_id", unique=True),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<SkillRelation {self.skill_id} -> {self.related_skill_id}>"
