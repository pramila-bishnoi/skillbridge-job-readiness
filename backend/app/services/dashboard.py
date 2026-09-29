"""Dashboard statistics.

Kept deliberately small: four headline tiles plus a little context. Building a
full analytics product here would add queries, indexes and cost for no teaching
value (project rule R9).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.enums import ApplicationStatus
from app.repositories.applications import ApplicationRepository
from app.repositories.jobs import JobRepository
from app.schemas.admin import (
    DailyCount,
    DashboardStats,
    DepartmentCount,
    LocationCount,
    RecentApplication,
    ScoreBucket,
    StatusCount,
)


class DashboardService:
    def __init__(self, db: Session):
        self.jobs = JobRepository(db)
        self.applications = ApplicationRepository(db)

    def stats(self) -> DashboardStats:
        by_status = self.applications.count_by_status()
        total = self.applications.count()
        with_resume = self.applications.count_with_resume()
        screening = sum(by_status.get(status, 0) for status in (
            ApplicationStatus.SCREENING,
            ApplicationStatus.INTERVIEW,
            ApplicationStatus.SELECTED,
        ))
        interview = sum(by_status.get(status, 0) for status in (
            ApplicationStatus.INTERVIEW,
            ApplicationStatus.SELECTED,
        ))
        selected = by_status.get(ApplicationStatus.SELECTED, 0)
        since = datetime.now(UTC).date() - timedelta(days=13)
        daily = self.applications.counts_by_day(datetime.combine(since, datetime.min.time(), tzinfo=UTC))
        return DashboardStats(
            active_jobs=self.jobs.count(is_active=True),
            total_jobs=self.jobs.count(),
            total_applications=self.applications.count(),
            interviews=by_status.get(ApplicationStatus.INTERVIEW, 0),
            selected=selected,
            rejected=by_status.get(ApplicationStatus.REJECTED, 0),
            # Every status is present even when its count is zero, so the UI
            # renders a stable set of bars instead of a shifting layout.
            applications_by_status=[
                StatusCount(status=status, count=by_status.get(status, 0))
                for status in ApplicationStatus
            ],
            applications_by_department=[
                DepartmentCount(department=department, count=count)
                for department, count in self.applications.count_by_department()
            ],
            recent_applications=[
                RecentApplication(
                    id=a.id,
                    application_code=a.application_code,
                    name=a.name,
                    job_title=a.job.title,
                    status=a.status,
                    created_at=a.created_at,
                    match_score=a.match_score,
                )
                for a in self.applications.recent(limit=6)
            ],
            with_resume=with_resume,
            without_resume=total - with_resume,
            resume_rate=round(with_resume / total * 100, 1) if total else 0.0,
            scored_applications=self.applications.count_scored(),
            average_match_score=self.applications.average_match_score(),
            screening_rate=round(screening / total * 100, 1) if total else 0.0,
            interview_rate=round(interview / total * 100, 1) if total else 0.0,
            hire_rate=round(selected / total * 100, 1) if total else 0.0,
            applications_by_location=[
                LocationCount(location=location, count=count)
                for location, count in self.applications.count_by_location()
            ],
            match_score_buckets=[
                ScoreBucket(label=label, count=count)
                for label, count in self.applications.match_score_buckets()
            ],
            applications_last_14_days=[
                DailyCount(day=since + timedelta(days=index), count=daily.get(since + timedelta(days=index), 0))
                for index in range(14)
            ],
            top_matches=[
                RecentApplication(
                    id=a.id,
                    application_code=a.application_code,
                    name=a.name,
                    job_title=a.job.title,
                    status=a.status,
                    created_at=a.created_at,
                    match_score=a.match_score,
                )
                for a in self.applications.top_by_match()
            ],
        )
