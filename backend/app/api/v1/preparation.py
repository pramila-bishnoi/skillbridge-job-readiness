"""Preparation-plan endpoints for SkillBridge Phase 5.

Nested under the job whose readiness analysis a plan is generated from
(``/student/jobs/{job_profile_id}/preparation``), the same sub-resource
convention Phase 4 set with ``.../readiness``. All routes are scoped to the
authenticated student.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentStudent, DbSession
from app.schemas.preparation import PreparationItemStatusUpdate, PreparationPlanDetail
from app.services.preparation import PreparationService

router = APIRouter(prefix="/student/jobs/{job_profile_id}/preparation", tags=["preparation plan"])


@router.post("", response_model=PreparationPlanDetail)
def generate_preparation_plan(
    job_profile_id: int, profile: CurrentStudent, db: DbSession
) -> PreparationPlanDetail:
    """Generate the plan from the job's latest readiness analysis (404 if
    none has been run). Safe to call again after the resume or job
    description changes and readiness has been rerun — regenerating merges
    into the existing plan rather than duplicating it."""
    return PreparationService(db).generate(profile, job_profile_id)


@router.get("", response_model=PreparationPlanDetail)
def get_preparation_plan(
    job_profile_id: int, profile: CurrentStudent, db: DbSession
) -> PreparationPlanDetail:
    """The current plan. 404 if ``POST`` has never been called for this job."""
    return PreparationService(db).get_for_student(profile, job_profile_id)


@router.patch("/items/{item_id}", response_model=PreparationPlanDetail)
def update_preparation_item_status(
    job_profile_id: int,
    item_id: int,
    payload: PreparationItemStatusUpdate,
    profile: CurrentStudent,
    db: DbSession,
) -> PreparationPlanDetail:
    return PreparationService(db).update_item_status(
        profile, job_profile_id, item_id, payload.status
    )
