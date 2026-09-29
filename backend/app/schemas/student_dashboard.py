"""Student dashboard-summary API contracts (Phase 7).

Named distinctly from ``schemas/admin.py``'s ``DashboardStats`` (the
recruiter/admin dashboard, inherited from the original ATS) — this is a
different audience and a different data source entirely.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.enums import SkillProgressStatus


class ReadinessSummaryEntry(BaseModel):
    job_profile_id: int
    title: str
    readiness_score: float


class RecentSkillProgressEntry(BaseModel):
    skill_id: int
    name: str
    status: SkillProgressStatus
    updated_at: datetime


class StudentDashboardSummary(BaseModel):
    tracked_skills_count: int
    not_started_count: int
    learning_count: int
    practiced_count: int
    confident_count: int

    analyzed_jobs_count: int
    # A plain average/max of existing Phase 4 readiness_score values — never
    # a new score and never fed back into services/readiness_scoring.py.
    average_readiness_score: float | None
    best_readiness_job: ReadinessSummaryEntry | None

    recent_skill_progress: list[RecentSkillProgressEntry]
