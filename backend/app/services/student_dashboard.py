"""Student dashboard-summary orchestration (Phase 7).

A read-only aggregation over existing data — skill progress (this phase) and
readiness analyses (Phase 4) — never a new computation. Does not import or
call ``services/readiness_scoring.py``; it only reads the ``readiness_score``
values Phase 4 already stored, the same way this service's admin-side
counterpart (``services/dashboard.py``) reads existing application rows
rather than recomputing anything.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.enums import SkillProgressStatus
from app.models.student_profile import StudentProfile
from app.repositories.job_profiles import JobProfileRepository
from app.repositories.match_analyses import MatchAnalysisRepository
from app.repositories.skill_progress import SkillProgressRepository
from app.schemas.student_dashboard import (
    ReadinessSummaryEntry,
    RecentSkillProgressEntry,
    StudentDashboardSummary,
)

RECENT_PROGRESS_LIMIT = 5


class StudentDashboardService:
    def __init__(self, db: Session):
        self.db = db
        self.job_profiles = JobProfileRepository(db)
        self.match_analyses = MatchAnalysisRepository(db)
        self.progress = SkillProgressRepository(db)

    def summary(self, profile: StudentProfile) -> StudentDashboardSummary:
        progress_rows = self.progress.list_for_student(profile.id)  # newest updated_at first
        counts = dict.fromkeys(SkillProgressStatus, 0)
        for row in progress_rows:
            counts[row.status] += 1

        analyses = self.match_analyses.list_for_student(profile.id)
        average_readiness = (
            round(sum(a.readiness_score for a in analyses) / len(analyses), 1) if analyses else None
        )

        best_readiness_job = None
        if analyses:
            best = max(analyses, key=lambda a: a.readiness_score)
            job_profile = self.job_profiles.get_by_id(best.job_profile_id)
            if job_profile is not None:
                best_readiness_job = ReadinessSummaryEntry(
                    job_profile_id=job_profile.id,
                    title=job_profile.title,
                    readiness_score=best.readiness_score,
                )

        return StudentDashboardSummary(
            tracked_skills_count=len(progress_rows),
            not_started_count=counts[SkillProgressStatus.NOT_STARTED],
            learning_count=counts[SkillProgressStatus.LEARNING],
            practiced_count=counts[SkillProgressStatus.PRACTICED],
            confident_count=counts[SkillProgressStatus.CONFIDENT],
            analyzed_jobs_count=len(analyses),
            average_readiness_score=average_readiness,
            best_readiness_job=best_readiness_job,
            recent_skill_progress=[
                RecentSkillProgressEntry(
                    skill_id=row.skill_id,
                    name=row.skill.name,
                    status=row.status,
                    updated_at=row.updated_at,
                )
                for row in progress_rows[:RECENT_PROGRESS_LIMIT]
            ],
        )
