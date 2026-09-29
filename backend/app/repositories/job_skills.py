"""Per-job normalized skill requirement persistence."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.enums import JobRequirementType
from app.models.job_skill import JobSkill
from app.services.skill_normalization import NormalizedSkillMatch


class JobSkillRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_for_job(self, job_profile_id: int) -> list[JobSkill]:
        stmt = (
            select(JobSkill)
            .options(joinedload(JobSkill.skill))
            .where(JobSkill.job_profile_id == job_profile_id)
            .order_by(JobSkill.skill_id)
        )
        return list(self.db.execute(stmt).scalars().all())

    def count_by_job(
        self, job_profile_ids: list[int]
    ) -> dict[int, dict[JobRequirementType, int]]:
        """One grouped query for a list view — avoids N+1 counting, mirroring
        ``JobRepository.application_counts``."""
        if not job_profile_ids:
            return {}
        stmt = (
            select(JobSkill.job_profile_id, JobSkill.requirement_type, func.count(JobSkill.id))
            .where(JobSkill.job_profile_id.in_(job_profile_ids))
            .group_by(JobSkill.job_profile_id, JobSkill.requirement_type)
        )
        counts: dict[int, dict[JobRequirementType, int]] = {}
        for job_profile_id, requirement_type, count in self.db.execute(stmt).all():
            counts.setdefault(job_profile_id, {})[requirement_type] = count
        return counts

    def replace_for_job(
        self,
        job_profile_id: int,
        required: list[NormalizedSkillMatch],
        preferred: list[NormalizedSkillMatch],
    ) -> None:
        """Re-analyzing a job profile fully replaces its previous skill
        evidence, the same replace semantics as StudentSkillRepository."""
        existing = self.db.execute(
            select(JobSkill).where(JobSkill.job_profile_id == job_profile_id)
        ).scalars().all()
        for row in existing:
            self.db.delete(row)
        self.db.flush()

        for match in required:
            self.db.add(
                JobSkill(
                    job_profile_id=job_profile_id,
                    skill_id=match.skill_id,
                    requirement_type=JobRequirementType.REQUIRED,
                    matched_text=match.matched_text,
                    match_type=match.match_type,
                )
            )
        for match in preferred:
            self.db.add(
                JobSkill(
                    job_profile_id=job_profile_id,
                    skill_id=match.skill_id,
                    requirement_type=JobRequirementType.PREFERRED,
                    matched_text=match.matched_text,
                    match_type=match.match_type,
                )
            )
        self.db.flush()
