"""Saved job-analysis endpoints for SkillBridge Phase 3.

All routes are scoped to the authenticated student (``CurrentStudent``, the
same dependency Phase 1/2's ``/student/profile*`` routes use) — there is no
route that lists or reads another student's saved job analyses.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import CurrentStudent, DbSession
from app.schemas.job_profile import JobProfileCreate, JobProfileDetail, JobProfileSummary
from app.schemas.job_url_import import JobUrlImportPreviewOut, JobUrlImportRequest
from app.services.job_profiles import JobProfileService
from app.services.job_url_import import JobUrlImportService

router = APIRouter(prefix="/student/jobs", tags=["job analysis"])


@router.post("", response_model=JobProfileDetail, status_code=status.HTTP_201_CREATED)
def create_job_profile(
    payload: JobProfileCreate, profile: CurrentStudent, db: DbSession
) -> JobProfileDetail:
    """Save a pasted job description and analyze it in the same request."""
    return JobProfileService(db).create(profile, payload)


@router.post("/import-url", response_model=JobUrlImportPreviewOut)
def preview_job_url_import(
    payload: JobUrlImportRequest, profile: CurrentStudent, db: DbSession
) -> JobUrlImportPreviewOut:
    """Fetch a public job-posting URL and return a preview. Nothing is saved
    here — the student reviews the preview and confirms via the existing
    ``POST /student/jobs`` (the same endpoint a pasted description uses)."""
    preview = JobUrlImportService(db).preview(payload.url)
    return JobUrlImportPreviewOut(**preview.__dict__)


@router.get("", response_model=list[JobProfileSummary])
def list_job_profiles(profile: CurrentStudent, db: DbSession) -> list[JobProfileSummary]:
    return JobProfileService(db).list_for_student(profile)


@router.get("/{job_profile_id}", response_model=JobProfileDetail)
def get_job_profile(
    job_profile_id: int, profile: CurrentStudent, db: DbSession
) -> JobProfileDetail:
    return JobProfileService(db).get_for_student(profile, job_profile_id)


@router.post("/{job_profile_id}/analyze", response_model=JobProfileDetail)
def analyze_job_profile(
    job_profile_id: int, profile: CurrentStudent, db: DbSession
) -> JobProfileDetail:
    """Re-run the deterministic analysis (e.g. after the skill catalog grows)."""
    return JobProfileService(db).reanalyze_for_student(profile, job_profile_id)
