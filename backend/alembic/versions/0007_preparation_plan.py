"""Add preparation plans and their per-skill preparation items.

Revision ID: 0007
Revises: 0006

Phase 5 (Personalized Skill-Gap Preparation Plan):

* ``preparation_plans`` — one row per (student, readiness analysis), the
  same "one active row, updated in place on regenerate" shape as
  ``match_analyses`` (migration 0006).
* ``preparation_items`` — one row per gap skill on that plan, carrying a
  deterministic priority (copied from ``skill_gaps.importance``), a
  template-generated reason, a per-skill learning-focus string, and the
  student's own progress status.

No seed data — the per-skill learning-focus text lives in code
(``app/core/skill_catalog.py`` ``LEARNING_FOCUS``), not the database, since
it is static reference text rather than a relational fact between rows.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JOB_REQUIREMENT_TYPES = ("REQUIRED", "PREFERRED")
SKILL_GAP_TYPES = ("MATCHED", "MISSING_REQUIRED", "MISSING_PREFERRED", "RELATED")
SKILL_GAP_IMPORTANCE = ("HIGH", "MEDIUM", "LOW")
PREPARATION_ITEM_STATUSES = ("NOT_STARTED", "IN_PROGRESS", "COMPLETED")


def upgrade() -> None:
    # --------------------------------------------------------- preparation_plans --
    op.create_table(
        "preparation_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_profile_id", sa.Integer(), nullable=False),
        sa.Column("match_analysis_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["student_profile_id"],
            ["student_profiles.id"],
            name="fk_preparation_plans_student_profile_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["match_analysis_id"],
            ["match_analyses.id"],
            name="fk_preparation_plans_match_analysis_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_preparation_plans_student_profile_id", "preparation_plans", ["student_profile_id"]
    )
    op.create_index(
        "ix_preparation_plans_match_analysis_id", "preparation_plans", ["match_analysis_id"]
    )
    op.create_index(
        "uq_preparation_plans_student_analysis",
        "preparation_plans",
        ["student_profile_id", "match_analysis_id"],
        unique=True,
    )

    # --------------------------------------------------------- preparation_items --
    op.create_table(
        "preparation_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("preparation_plan_id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column(
            "requirement_type",
            sa.Enum(*JOB_REQUIREMENT_TYPES, name="jobrequirementtype", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column(
            "gap_type",
            sa.Enum(*SKILL_GAP_TYPES, name="skillgaptype", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column(
            "priority",
            sa.Enum(*SKILL_GAP_IMPORTANCE, name="skillgapimportance", native_enum=False, length=10),
            nullable=False,
        ),
        sa.Column("reason", sa.String(length=300), nullable=False),
        sa.Column("learning_focus", sa.String(length=300), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                *PREPARATION_ITEM_STATUSES, name="preparationitemstatus", native_enum=False, length=20
            ),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["preparation_plan_id"],
            ["preparation_plans.id"],
            name="fk_preparation_items_preparation_plan_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["skill_id"], ["skills.id"], name="fk_preparation_items_skill_id", ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_preparation_items_preparation_plan_id", "preparation_items", ["preparation_plan_id"]
    )
    op.create_index("ix_preparation_items_skill_id", "preparation_items", ["skill_id"])
    op.create_index(
        "uq_preparation_items_plan_skill",
        "preparation_items",
        ["preparation_plan_id", "skill_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_preparation_items_plan_skill", table_name="preparation_items")
    op.drop_index("ix_preparation_items_skill_id", table_name="preparation_items")
    op.drop_index("ix_preparation_items_preparation_plan_id", table_name="preparation_items")
    op.drop_table("preparation_items")

    op.drop_index("uq_preparation_plans_student_analysis", table_name="preparation_plans")
    op.drop_index("ix_preparation_plans_match_analysis_id", table_name="preparation_plans")
    op.drop_index("ix_preparation_plans_student_profile_id", table_name="preparation_plans")
    op.drop_table("preparation_plans")
