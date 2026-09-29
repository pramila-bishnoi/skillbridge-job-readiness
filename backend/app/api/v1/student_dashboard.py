"""Student dashboard-summary endpoint for SkillBridge Phase 7."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentStudent, DbSession
from app.schemas.student_dashboard import StudentDashboardSummary
from app.services.student_dashboard import StudentDashboardService

router = APIRouter(prefix="/student/dashboard", tags=["student dashboard"])


@router.get("", response_model=StudentDashboardSummary)
def get_student_dashboard(profile: CurrentStudent, db: DbSession) -> StudentDashboardSummary:
    return StudentDashboardService(db).summary(profile)
