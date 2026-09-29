"""Explicit skill-relationship persistence (Phase 4)."""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.skill_catalog import normalize_key
from app.models.skill import Skill
from app.models.skill_relation import SkillRelation


class SkillRelationRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_related(self, skill_ids: Iterable[int]) -> dict[int, set[int]]:
        """``{skill_id: {ids of skills related to it}}`` for the given ids —
        one batched query, mirroring ``JobSkillRepository.count_by_job``."""
        skill_ids = list(skill_ids)
        if not skill_ids:
            return {}
        stmt = select(SkillRelation.skill_id, SkillRelation.related_skill_id).where(
            SkillRelation.skill_id.in_(skill_ids)
        )
        related: dict[int, set[int]] = {}
        for skill_id, related_skill_id in self.db.execute(stmt).all():
            related.setdefault(skill_id, set()).add(related_skill_id)
        return related

    def bulk_upsert_relationships(self, pairs: Iterable[tuple[str, str]]) -> None:
        """Idempotent insert of the seed relationships, keyed by skill name.

        Real environments get these from Alembic migration 0006; this method
        exists so the pytest fixture (``create_all``, no migrations —
        CLAUDE.md §7) seeds the exact same data.
        """
        skills_by_key = {
            skill.normalized_key: skill for skill in self.db.execute(select(Skill)).scalars()
        }
        existing = {
            (row.skill_id, row.related_skill_id)
            for row in self.db.execute(select(SkillRelation)).scalars()
        }
        for name_a, name_b in pairs:
            skill_a = skills_by_key.get(normalize_key(name_a))
            skill_b = skills_by_key.get(normalize_key(name_b))
            if skill_a is None or skill_b is None:
                continue
            for left, right in ((skill_a, skill_b), (skill_b, skill_a)):
                if (left.id, right.id) not in existing:
                    self.db.add(SkillRelation(skill_id=left.id, related_skill_id=right.id))
                    existing.add((left.id, right.id))
        self.db.commit()
