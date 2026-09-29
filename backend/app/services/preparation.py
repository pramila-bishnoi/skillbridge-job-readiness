"""Preparation-plan orchestration (Phase 5).

Turns the missing/related ``SkillGap`` rows behind one Phase 4
``MatchAnalysis`` into a ``PreparationPlan``. Does not touch
``services/readiness_scoring.py`` at all — priority is copied straight from
``SkillGap.importance``, which that module already computed; this service
only adds the explanatory text (``services/preparation_guidance``) and
persistence.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import (
    JobProfileNotFoundError,
    MatchAnalysisNotFoundError,
    PreparationItemNotFoundError,
    PreparationPlanNotFoundError,
)
from app.models.enums import PreparationItemStatus, SkillGapType
from app.models.job_profile import JobProfile
from app.models.match_analysis import MatchAnalysis
from app.models.preparation_item import PreparationItem
from app.models.preparation_plan import PreparationPlan
from app.models.student_profile import StudentProfile
from app.repositories.job_profiles import JobProfileRepository
from app.repositories.match_analyses import MatchAnalysisRepository
from app.repositories.preparation_items import PreparationItemRepository
from app.repositories.preparation_plans import PreparationPlanRepository
from app.repositories.skill_gaps import SkillGapRepository
from app.schemas.preparation import PreparationItemOut, PreparationPlanDetail
from app.services.preparation_guidance import GeneratedItem, learning_focus_for, reason_for

# The gap types a plan item makes sense for — the same set Phase 4's own
# "gaps" view uses (readiness.py's _GAP_TYPES). A MATCHED skill never gets a
# preparation item: there is nothing to prepare.
_GAP_TYPES = (SkillGapType.MISSING_REQUIRED, SkillGapType.MISSING_PREFERRED, SkillGapType.RELATED)

_PRIORITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


class PreparationService:
    def __init__(self, db: Session):
        self.db = db
        self.job_profiles = JobProfileRepository(db)
        self.match_analyses = MatchAnalysisRepository(db)
        self.skill_gaps = SkillGapRepository(db)
        self.plans = PreparationPlanRepository(db)
        self.items = PreparationItemRepository(db)

    def generate(self, profile: StudentProfile, job_profile_id: int) -> PreparationPlanDetail:
        """Generate (or regenerate) the plan from the job's latest readiness
        analysis. Safe to call repeatedly: the plan is one row per
        (student, analysis) — see PreparationPlan's unique constraint — and
        regenerating merges into existing items rather than replacing them
        wholesale, so a student's own progress on a still-open gap survives."""
        job_profile = self._get_owned_job_or_404(profile, job_profile_id)
        analysis = self._get_analysis_or_404(profile, job_profile)

        gap_rows = self.skill_gaps.list_for_analysis(analysis.id, gap_types=list(_GAP_TYPES))
        generated = [
            GeneratedItem(
                skill_id=gap.skill_id,
                requirement_type=gap.requirement_type,
                gap_type=gap.gap_type,
                priority=gap.importance,
                reason=reason_for(
                    gap_type=gap.gap_type,
                    job_title=job_profile.title,
                    skill_name=gap.skill.name,
                    related_to_skill_name=gap.related_to_skill.name if gap.related_to_skill else None,
                ),
                learning_focus=learning_focus_for(gap.skill.name),
            )
            for gap in gap_rows
        ]

        plan = self.plans.get_by_student_and_analysis(profile.id, analysis.id)
        if plan is None:
            plan = self.plans.add(
                PreparationPlan(student_profile_id=profile.id, match_analysis_id=analysis.id)
            )

        self.items.replace_for_plan(plan.id, generated)
        self.db.commit()
        self.db.refresh(plan)
        return self._to_detail(plan, job_profile, analysis)

    def get_for_student(self, profile: StudentProfile, job_profile_id: int) -> PreparationPlanDetail:
        job_profile = self._get_owned_job_or_404(profile, job_profile_id)
        analysis = self._get_analysis_or_404(profile, job_profile)
        plan = self.plans.get_by_student_and_analysis(profile.id, analysis.id)
        if plan is None:
            raise PreparationPlanNotFoundError()
        return self._to_detail(plan, job_profile, analysis)

    def update_item_status(
        self,
        profile: StudentProfile,
        job_profile_id: int,
        item_id: int,
        status: PreparationItemStatus,
    ) -> PreparationPlanDetail:
        job_profile = self._get_owned_job_or_404(profile, job_profile_id)
        analysis = self._get_analysis_or_404(profile, job_profile)
        plan = self.plans.get_by_student_and_analysis(profile.id, analysis.id)
        if plan is None:
            raise PreparationPlanNotFoundError()

        item = self.items.get_by_id_for_plan(plan.id, item_id)
        if item is None:
            raise PreparationItemNotFoundError()

        item.status = status
        self.db.commit()
        self.db.refresh(plan)
        return self._to_detail(plan, job_profile, analysis)

    # ------------------------------------------------------------ internals --
    def _get_owned_job_or_404(self, profile: StudentProfile, job_profile_id: int) -> JobProfile:
        job_profile = self.job_profiles.get_by_id(job_profile_id)
        if job_profile is None or job_profile.student_profile_id != profile.id:
            raise JobProfileNotFoundError()
        return job_profile

    def _get_analysis_or_404(self, profile: StudentProfile, job_profile: JobProfile) -> MatchAnalysis:
        analysis = self.match_analyses.get_by_student_and_job(profile.id, job_profile.id)
        if analysis is None:
            raise MatchAnalysisNotFoundError()
        return analysis

    def _to_detail(
        self, plan: PreparationPlan, job_profile: JobProfile, analysis: MatchAnalysis
    ) -> PreparationPlanDetail:
        rows = sorted(
            self.items.list_for_plan(plan.id),
            key=lambda row: (_PRIORITY_ORDER[row.priority.value], row.skill.name),
        )
        items = [self._to_item_out(row) for row in rows]
        total = len(items)
        completed = sum(1 for row in rows if row.status == PreparationItemStatus.COMPLETED)
        in_progress = sum(1 for row in rows if row.status == PreparationItemStatus.IN_PROGRESS)
        not_started = total - completed - in_progress
        return PreparationPlanDetail(
            id=plan.id,
            job_profile_id=job_profile.id,
            job_title=job_profile.title,
            match_analysis_id=analysis.id,
            readiness_score=analysis.readiness_score,
            total_items=total,
            completed_items=completed,
            in_progress_items=in_progress,
            not_started_items=not_started,
            progress_percent=round(completed / total * 100, 1) if total else 0.0,
            items=items,
            created_at=plan.created_at,
            updated_at=plan.updated_at,
        )

    @staticmethod
    def _to_item_out(row: PreparationItem) -> PreparationItemOut:
        return PreparationItemOut(
            id=row.id,
            skill_id=row.skill_id,
            name=row.skill.name,
            category=row.skill.category,
            requirement_type=row.requirement_type,
            gap_type=row.gap_type,
            priority=row.priority,
            reason=row.reason,
            learning_focus=row.learning_focus,
            status=row.status,
        )
