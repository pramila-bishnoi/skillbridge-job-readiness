"""Canonical skill catalog persistence."""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.skill_catalog import SkillSeed, normalize_key
from app.models.skill import Skill, SkillAlias


class SkillRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_catalog(self) -> list[Skill]:
        """Every active skill with its aliases eagerly loaded, for normalization."""
        stmt = (
            select(Skill).where(Skill.is_active.is_(True)).options(selectinload(Skill.aliases))
        )
        return list(self.db.execute(stmt).scalars().unique().all())

    def get_by_id(self, skill_id: int) -> Skill | None:
        """Phase 7: validates a skill id coming directly from a URL path
        (``PATCH .../skill-progress/{skill_id}``) — the first time a raw
        skill id is accepted as user input rather than derived internally."""
        return self.db.get(Skill, skill_id)

    def bulk_upsert_catalog(self, seeds: Iterable[SkillSeed]) -> None:
        """Idempotent insert of the seed catalog, keyed by ``normalized_key``.

        Real environments get the catalog from Alembic migration 0004; this
        method exists so the pytest fixture — which builds its schema with
        ``create_all`` and therefore never runs that migration — seeds the
        exact same data (CLAUDE.md §7).
        """
        for seed in seeds:
            key = normalize_key(seed.name)
            skill = self.db.execute(select(Skill).where(Skill.normalized_key == key)).scalar_one_or_none()
            if skill is None:
                skill = Skill(name=seed.name, normalized_key=key, category=seed.category)
                self.db.add(skill)
                self.db.flush()
            existing_alias_keys = {
                alias.normalized_key
                for alias in self.db.execute(
                    select(SkillAlias).where(SkillAlias.skill_id == skill.id)
                ).scalars()
            }
            for alias in seed.aliases:
                alias_key = normalize_key(alias)
                if alias_key not in existing_alias_keys:
                    self.db.add(SkillAlias(skill_id=skill.id, alias=alias, normalized_key=alias_key))
        self.db.commit()
