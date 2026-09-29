"""Version 1 of the public API.

Everything is mounted under ``/api/v1`` so a future v2 can coexist with it
instead of breaking every deployed React bundle.
"""

from fastapi import APIRouter

from app.api.v1 import (
    admin_applications,
    admin_auth,
    admin_jobs,
    admin_stats,
    applications,
    interview_prep,
    job_analysis,
    job_comparison,
    jobs,
    preparation,
    readiness,
    skill_progress,
    student_dashboard,
    student_profiles,
)

api_router = APIRouter()
api_router.include_router(jobs.router)
api_router.include_router(applications.router)
api_router.include_router(admin_auth.router)
api_router.include_router(admin_jobs.router)
api_router.include_router(admin_applications.router)
api_router.include_router(admin_stats.router)
api_router.include_router(student_profiles.router)
api_router.include_router(job_analysis.router)
api_router.include_router(readiness.router)
api_router.include_router(preparation.router)
api_router.include_router(interview_prep.router)
api_router.include_router(job_comparison.router)
api_router.include_router(skill_progress.router)
api_router.include_router(student_dashboard.router)

__all__ = ["api_router"]
