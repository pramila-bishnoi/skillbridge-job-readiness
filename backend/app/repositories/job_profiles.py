"""Saved job-analysis persistence."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job_profile import JobProfile


class JobProfileRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, job_profile_id: int) -> JobProfile | None:
        return self.db.get(JobProfile, job_profile_id)

    def list_for_student(self, student_profile_id: int) -> list[JobProfile]:
        stmt = (
            select(JobProfile)
            .where(JobProfile.student_profile_id == student_profile_id)
            .order_by(JobProfile.created_at.desc(), JobProfile.id.desc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def add(self, job_profile: JobProfile) -> JobProfile:
        self.db.add(job_profile)
        self.db.flush()
        return job_profile
