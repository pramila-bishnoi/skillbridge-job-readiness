"""Preparation-plan persistence (Phase 5)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.preparation_plan import PreparationPlan


class PreparationPlanRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_student_and_analysis(
        self, student_profile_id: int, match_analysis_id: int
    ) -> PreparationPlan | None:
        stmt = select(PreparationPlan).where(
            PreparationPlan.student_profile_id == student_profile_id,
            PreparationPlan.match_analysis_id == match_analysis_id,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def add(self, plan: PreparationPlan) -> PreparationPlan:
        self.db.add(plan)
        self.db.flush()
        return plan
