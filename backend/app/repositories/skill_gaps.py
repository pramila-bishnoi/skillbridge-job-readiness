"""Per-analysis skill-gap breakdown persistence (Phase 4)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.enums import SkillGapType
from app.models.skill_gap import SkillGap
from app.services.readiness_scoring import SkillClassification


class SkillGapRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_for_analysis(
        self, match_analysis_id: int, *, gap_types: list[SkillGapType] | None = None
    ) -> list[SkillGap]:
        stmt = (
            select(SkillGap)
            .options(joinedload(SkillGap.skill), joinedload(SkillGap.related_to_skill))
            .where(SkillGap.match_analysis_id == match_analysis_id)
            .order_by(SkillGap.skill_id)
        )
        if gap_types:
            stmt = stmt.where(SkillGap.gap_type.in_(gap_types))
        return list(self.db.execute(stmt).scalars().all())

    def replace_for_analysis(
        self, match_analysis_id: int, classifications: list[SkillClassification]
    ) -> None:
        """A rerun fully replaces the previous breakdown — same replace
        semantics as Student/JobSkillRepository."""
        existing = self.db.execute(
            select(SkillGap).where(SkillGap.match_analysis_id == match_analysis_id)
        ).scalars().all()
        for row in existing:
            self.db.delete(row)
        self.db.flush()

        for item in classifications:
            self.db.add(
                SkillGap(
                    match_analysis_id=match_analysis_id,
                    skill_id=item.skill_id,
                    requirement_type=item.requirement_type,
                    gap_type=item.gap_type,
                    importance=item.importance,
                    evidence=item.evidence,
                    related_to_skill_id=item.related_to_skill_id,
                )
            )
        self.db.flush()
