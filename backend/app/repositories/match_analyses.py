"""Job-readiness analysis persistence (Phase 4)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.match_analysis import MatchAnalysis


class MatchAnalysisRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_student_and_job(
        self, student_profile_id: int, job_profile_id: int
    ) -> MatchAnalysis | None:
        stmt = select(MatchAnalysis).where(
            MatchAnalysis.student_profile_id == student_profile_id,
            MatchAnalysis.job_profile_id == job_profile_id,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_for_jobs(self, student_profile_id: int, job_profile_ids: list[int]) -> list[MatchAnalysis]:
        """Phase 7 (job comparison): every existing analysis among the given
        jobs, in one query — comparison never triggers a new analysis."""
        stmt = select(MatchAnalysis).where(
            MatchAnalysis.student_profile_id == student_profile_id,
            MatchAnalysis.job_profile_id.in_(job_profile_ids),
        )
        return list(self.db.execute(stmt).scalars().all())

    def list_for_student(self, student_profile_id: int) -> list[MatchAnalysis]:
        """Phase 7 (dashboard summary): every analysis this student has run,
        for a simple average/best-score display — never a new computation."""
        stmt = select(MatchAnalysis).where(MatchAnalysis.student_profile_id == student_profile_id)
        return list(self.db.execute(stmt).scalars().all())

    def upsert(self, *, student_profile_id: int, job_profile_id: int, **fields: object) -> MatchAnalysis:
        """One row per (student, job) — a rerun updates it in place, which is
        what makes "avoid creating duplicate active analyses" true by
        construction rather than by a cleanup step."""
        analysis = self.get_by_student_and_job(student_profile_id, job_profile_id)
        if analysis is None:
            analysis = MatchAnalysis(
                student_profile_id=student_profile_id, job_profile_id=job_profile_id
            )
            self.db.add(analysis)
        for field, value in fields.items():
            setattr(analysis, field, value)
        self.db.flush()
        return analysis
