"""Skill-progress orchestration (Phase 7).

Deliberately small: unlike readiness/preparation/interview prep, there is no
generation step here — a student sets their own status directly. The only
business rule is that the skill id must exist in the canonical catalog
(Phase 2); nothing here reads or writes ``SkillGap``, ``MatchAnalysis``, or
any other phase's data.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import SkillNotFoundError
from app.models.enums import SkillProgressStatus
from app.models.skill_progress import SkillProgress
from app.models.student_profile import StudentProfile
from app.repositories.skill_progress import SkillProgressRepository
from app.repositories.skills import SkillRepository
from app.schemas.skill_progress import SkillCatalogEntry, SkillProgressOut


class SkillProgressService:
    def __init__(self, db: Session):
        self.db = db
        self.skills = SkillRepository(db)
        self.progress = SkillProgressRepository(db)

    def list_for_student(self, profile: StudentProfile) -> list[SkillProgressOut]:
        return [self._to_out(row) for row in self.progress.list_for_student(profile.id)]

    def list_catalog(self) -> list[SkillCatalogEntry]:
        """Every skill a student could choose to track — not just ones
        already extracted from their resume."""
        return [
            SkillCatalogEntry(skill_id=skill.id, name=skill.name, category=skill.category)
            for skill in sorted(self.skills.list_catalog(), key=lambda s: s.name)
        ]

    def update(
        self, profile: StudentProfile, skill_id: int, status: SkillProgressStatus
    ) -> SkillProgressOut:
        if self.skills.get_by_id(skill_id) is None:
            raise SkillNotFoundError()
        progress = self.progress.upsert(profile.id, skill_id, status)
        self.db.commit()
        self.db.refresh(progress)
        return self._to_out(progress)

    @staticmethod
    def _to_out(row: SkillProgress) -> SkillProgressOut:
        return SkillProgressOut(
            skill_id=row.skill_id,
            name=row.skill.name,
            category=row.skill.category,
            status=row.status,
            updated_at=row.updated_at,
        )
