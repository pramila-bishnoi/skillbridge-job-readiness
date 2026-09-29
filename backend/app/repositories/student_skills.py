"""Per-student normalized skill evidence persistence."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.student_skill import StudentSkill
from app.services.skill_normalization import NormalizedSkillMatch


class StudentSkillRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_for_profile(self, profile_id: int) -> list[StudentSkill]:
        stmt = (
            select(StudentSkill)
            .options(joinedload(StudentSkill.skill))
            .where(StudentSkill.student_profile_id == profile_id)
            .order_by(StudentSkill.skill_id)
        )
        return list(self.db.execute(stmt).scalars().all())

    def replace_for_profile(self, profile_id: int, matches: list[NormalizedSkillMatch]) -> None:
        """A re-uploaded resume's matches fully replace the previous evidence
        rather than accumulating stale rows from an earlier file."""
        existing = self.db.execute(
            select(StudentSkill).where(StudentSkill.student_profile_id == profile_id)
        ).scalars().all()
        for row in existing:
            self.db.delete(row)
        self.db.flush()

        for match in matches:
            self.db.add(
                StudentSkill(
                    student_profile_id=profile_id,
                    skill_id=match.skill_id,
                    matched_text=match.matched_text,
                    match_type=match.match_type,
                )
            )
        self.db.flush()
