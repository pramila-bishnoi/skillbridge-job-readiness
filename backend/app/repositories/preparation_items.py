"""Preparation-item persistence (Phase 5)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.enums import PreparationItemStatus
from app.models.preparation_item import PreparationItem
from app.services.preparation_guidance import GeneratedItem


class PreparationItemRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_for_plan(self, preparation_plan_id: int) -> list[PreparationItem]:
        stmt = (
            select(PreparationItem)
            .options(joinedload(PreparationItem.skill))
            .where(PreparationItem.preparation_plan_id == preparation_plan_id)
            .order_by(PreparationItem.skill_id)
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_by_id_for_plan(
        self, preparation_plan_id: int, item_id: int
    ) -> PreparationItem | None:
        stmt = select(PreparationItem).where(
            PreparationItem.id == item_id,
            PreparationItem.preparation_plan_id == preparation_plan_id,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def replace_for_plan(self, preparation_plan_id: int, generated: list[GeneratedItem]) -> None:
        """Merges the freshly generated gap list into the plan rather than a
        blind delete-then-recreate: a skill that is still a gap keeps its
        existing row (and therefore its ``status`` — a student's own
        progress must survive a regenerate), a skill no longer a gap is
        removed, and a newly-appeared gap is inserted as ``NOT_STARTED``.
        """
        existing_by_skill = {
            row.skill_id: row
            for row in self.db.execute(
                select(PreparationItem).where(
                    PreparationItem.preparation_plan_id == preparation_plan_id
                )
            ).scalars()
        }
        generated_skill_ids = {item.skill_id for item in generated}

        for skill_id, row in existing_by_skill.items():
            if skill_id not in generated_skill_ids:
                self.db.delete(row)

        for item in generated:
            row = existing_by_skill.get(item.skill_id)
            if row is not None:
                row.requirement_type = item.requirement_type
                row.gap_type = item.gap_type
                row.priority = item.priority
                row.reason = item.reason
                row.learning_focus = item.learning_focus
                # status is deliberately left untouched.
            else:
                self.db.add(
                    PreparationItem(
                        preparation_plan_id=preparation_plan_id,
                        skill_id=item.skill_id,
                        requirement_type=item.requirement_type,
                        gap_type=item.gap_type,
                        priority=item.priority,
                        reason=item.reason,
                        learning_focus=item.learning_focus,
                        status=PreparationItemStatus.NOT_STARTED,
                    )
                )
        self.db.flush()
