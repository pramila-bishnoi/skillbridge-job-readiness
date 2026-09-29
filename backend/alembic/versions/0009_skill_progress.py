"""Add student skill-progress tracking.

Revision ID: 0009
Revises: 0008

Phase 7 (Job Comparison + Skill Progress Tracking):

* ``skill_progress`` — one row per (student, skill) a student has explicitly
  set a status for (NOT_STARTED/LEARNING/PRACTICED/CONFIDENT); sparse, not
  auto-created for every catalog or resume skill.

Job comparison adds no table of its own — it is a stateless read over
existing ``match_analyses``/``skill_gaps`` rows (Phase 4), computed fresh on
every request rather than persisted.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SKILL_PROGRESS_STATUSES = ("NOT_STARTED", "LEARNING", "PRACTICED", "CONFIDENT")


def upgrade() -> None:
    op.create_table(
        "skill_progress",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_profile_id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(*SKILL_PROGRESS_STATUSES, name="skillprogressstatus", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["student_profile_id"],
            ["student_profiles.id"],
            name="fk_skill_progress_student_profile_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["skill_id"], ["skills.id"], name="fk_skill_progress_skill_id", ondelete="CASCADE"
        ),
    )
    op.create_index("ix_skill_progress_student_profile_id", "skill_progress", ["student_profile_id"])
    op.create_index("ix_skill_progress_skill_id", "skill_progress", ["skill_id"])
    op.create_index(
        "uq_skill_progress_student_skill", "skill_progress", ["student_profile_id", "skill_id"], unique=True
    )


def downgrade() -> None:
    op.drop_index("uq_skill_progress_student_skill", table_name="skill_progress")
    op.drop_index("ix_skill_progress_skill_id", table_name="skill_progress")
    op.drop_index("ix_skill_progress_student_profile_id", table_name="skill_progress")
    op.drop_table("skill_progress")
