"""Skill-progress persistence (Phase 7)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.enums import SkillProgressStatus
from app.models.skill_progress import SkillProgress


class SkillProgressRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_for_student(self, student_profile_id: int) -> list[SkillProgress]:
        stmt = (
            select(SkillProgress)
            .options(joinedload(SkillProgress.skill))
            .where(SkillProgress.student_profile_id == student_profile_id)
            .order_by(SkillProgress.updated_at.desc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_by_student_and_skill(
        self, student_profile_id: int, skill_id: int
    ) -> SkillProgress | None:
        stmt = select(SkillProgress).where(
            SkillProgress.student_profile_id == student_profile_id,
            SkillProgress.skill_id == skill_id,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def upsert(
        self, student_profile_id: int, skill_id: int, status: SkillProgressStatus
    ) -> SkillProgress:
        """One row per (student, skill) — setting a status again just moves
        the existing row's ``status`` (and, via ``TimestampMixin``,
        ``updated_at``) rather than creating a second row."""
        progress = self.get_by_student_and_skill(student_profile_id, skill_id)
        if progress is None:
            progress = SkillProgress(
                student_profile_id=student_profile_id, skill_id=skill_id, status=status
            )
            self.db.add(progress)
        else:
            progress.status = status
        self.db.flush()
        return progress
