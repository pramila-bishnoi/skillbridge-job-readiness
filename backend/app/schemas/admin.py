"""Admin profile and dashboard-statistics schemas."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.enums import ApplicationStatus


class AdminProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str | None = None
    is_active: bool


class StatusCount(BaseModel):
    status: ApplicationStatus
    count: int


class DepartmentCount(BaseModel):
    department: str
    count: int


class RecentApplication(BaseModel):
    id: int
    application_code: str
    name: str
    job_title: str
    status: ApplicationStatus
    created_at: datetime
    match_score: float | None = None


class LocationCount(BaseModel):
    location: str
    count: int


class ScoreBucket(BaseModel):
    label: str
    count: int


class DailyCount(BaseModel):
    day: date
    count: int


class DashboardStats(BaseModel):
    """Headline hiring tiles plus recruiter analytics (match quality, funnel, volume)."""

    active_jobs: int
    total_jobs: int
    total_applications: int
    interviews: int
    selected: int
    rejected: int
    applications_by_status: list[StatusCount]
    applications_by_department: list[DepartmentCount]
    recent_applications: list[RecentApplication]
    with_resume: int
    without_resume: int
    resume_rate: float
    scored_applications: int
    average_match_score: float | None = None
    screening_rate: float
    interview_rate: float
    hire_rate: float
    applications_by_location: list[LocationCount]
    match_score_buckets: list[ScoreBucket]
    applications_last_14_days: list[DailyCount]
    top_matches: list[RecentApplication]
