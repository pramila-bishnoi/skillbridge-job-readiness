"""Interview-preparation endpoints for SkillBridge Phase 6.

Nested under the job whose readiness analysis interview prep is generated
from (``/student/jobs/{job_profile_id}/interview-prep``), the same
sub-resource convention Phase 4/5 use for ``.../readiness`` and
``.../preparation``.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentStudent, DbSession
from app.schemas.interview_prep import InterviewPrepDetail, InterviewQuestionCompletedUpdate
from app.services.interview_prep import InterviewPrepService

router = APIRouter(
    prefix="/student/jobs/{job_profile_id}/interview-prep", tags=["interview preparation"]
)


@router.post("", response_model=InterviewPrepDetail)
def generate_interview_prep(
    job_profile_id: int, profile: CurrentStudent, db: DbSession
) -> InterviewPrepDetail:
    """Generate (or regenerate) interview prep from the job's latest
    readiness analysis (404 if none has been run)."""
    return InterviewPrepService(db).generate(profile, job_profile_id)


@router.get("", response_model=InterviewPrepDetail)
def get_interview_prep(
    job_profile_id: int, profile: CurrentStudent, db: DbSession
) -> InterviewPrepDetail:
    """The current interview prep set. 404 if ``POST`` has never been called."""
    return InterviewPrepService(db).get_for_student(profile, job_profile_id)


@router.patch("/questions/{question_id}", response_model=InterviewPrepDetail)
def update_interview_question_completed(
    job_profile_id: int,
    question_id: int,
    payload: InterviewQuestionCompletedUpdate,
    profile: CurrentStudent,
    db: DbSession,
) -> InterviewPrepDetail:
    return InterviewPrepService(db).update_question_completed(
        profile, job_profile_id, question_id, payload.completed
    )
