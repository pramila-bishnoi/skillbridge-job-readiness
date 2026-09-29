"""Job-readiness analysis endpoints for SkillBridge Phase 4.

Nested under the saved job it analyzes (``/student/jobs/{job_profile_id}/
readiness``), the same sub-resource pattern Phase 3 uses for
``/student/jobs/{job_profile_id}/analyze``. All routes are scoped to the
authenticated student; a job profile owned by someone else reads as 404, the
same posture Phase 3's own routes already use.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentStudent, DbSession
from app.schemas.readiness import MatchAnalysisDetail, SkillGapOut
from app.services.readiness import ReadinessService

router = APIRouter(prefix="/student/jobs/{job_profile_id}/readiness", tags=["job readiness"])


@router.post("", response_model=MatchAnalysisDetail)
def analyze_readiness(
    job_profile_id: int, profile: CurrentStudent, db: DbSession
) -> MatchAnalysisDetail:
    """Compute (or recompute) readiness. Rerunning after a resume re-upload
    or a job re-analysis updates the one existing analysis in place."""
    return ReadinessService(db).analyze(profile, job_profile_id)


@router.get("", response_model=MatchAnalysisDetail)
def get_readiness(
    job_profile_id: int, profile: CurrentStudent, db: DbSession
) -> MatchAnalysisDetail:
    """The latest stored analysis. 404 if ``POST`` has never been called for
    this job."""
    return ReadinessService(db).get_latest_for_student(profile, job_profile_id)


@router.get("/matched", response_model=list[SkillGapOut])
def get_matched_skills(
    job_profile_id: int, profile: CurrentStudent, db: DbSession
) -> list[SkillGapOut]:
    return ReadinessService(db).list_matched(profile, job_profile_id)


@router.get("/missing", response_model=list[SkillGapOut])
def get_missing_skills(
    job_profile_id: int, profile: CurrentStudent, db: DbSession
) -> list[SkillGapOut]:
    return ReadinessService(db).list_missing(profile, job_profile_id)


@router.get("/gaps", response_model=list[SkillGapOut])
def get_skill_gaps(
    job_profile_id: int, profile: CurrentStudent, db: DbSession
) -> list[SkillGapOut]:
    return ReadinessService(db).list_gaps(profile, job_profile_id)
