"""Job-comparison endpoint for SkillBridge Phase 7.

A separate top-level resource, not nested under ``/student/jobs/{id}`` —
unlike readiness/preparation/interview-prep, a comparison spans several jobs
at once, so it has no single job to nest under.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentStudent, DbSession
from app.schemas.job_comparison import JobComparisonRequest, JobComparisonResult
from app.services.job_comparison import JobComparisonService

router = APIRouter(prefix="/student/job-comparison", tags=["job comparison"])


@router.post("", response_model=JobComparisonResult)
def compare_jobs(
    payload: JobComparisonRequest, profile: CurrentStudent, db: DbSession
) -> JobComparisonResult:
    """Compare 2-5 of the student's own saved jobs. Every job must already
    have a readiness analysis (409 naming which ones don't) — comparison
    never triggers one itself."""
    return JobComparisonService(db).compare(profile, payload.job_profile_ids)
