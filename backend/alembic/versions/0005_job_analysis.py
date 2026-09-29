"""Add saved job analyses (job_profiles) and their normalized requirements (job_skills).

Revision ID: 0005
Revises: 0004

Phase 3 (Job Description Intelligence): a student can paste a job description
and save it as a ``job_profiles`` row; ``job_skills`` links it to the existing
``skills`` catalog (Phase 2, migration 0004) the same way ``student_skills``
does for a resume, with a ``requirement_type`` distinguishing required from
preferred. No seed data — this migration only adds structure.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JOB_REQUIREMENT_TYPES = ("REQUIRED", "PREFERRED")
SKILL_MATCH_TYPES = ("CANONICAL_NAME", "ALIAS")


def upgrade() -> None:
    # ---------------------------------------------------------- job_profiles --
    op.create_table(
        "job_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_profile_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("company", sa.String(length=150), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("experience_required", sa.String(length=100), nullable=True),
        sa.Column("experience_evidence", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["student_profile_id"],
            ["student_profiles.id"],
            name="fk_job_profiles_student_profile_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_job_profiles_student_profile_id", "job_profiles", ["student_profile_id"])

    # ------------------------------------------------------------- job_skills --
    op.create_table(
        "job_skills",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_profile_id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column(
            "requirement_type",
            sa.Enum(*JOB_REQUIREMENT_TYPES, name="jobrequirementtype", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column("matched_text", sa.String(length=200), nullable=False),
        sa.Column(
            "match_type",
            sa.Enum(*SKILL_MATCH_TYPES, name="skillmatchtype", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["job_profile_id"], ["job_profiles.id"], name="fk_job_skills_job_profile_id", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["skill_id"], ["skills.id"], name="fk_job_skills_skill_id", ondelete="CASCADE"
        ),
    )
    op.create_index("ix_job_skills_job_profile_id", "job_skills", ["job_profile_id"])
    op.create_index("ix_job_skills_skill_id", "job_skills", ["skill_id"])
    op.create_index(
        "uq_job_skills_profile_skill", "job_skills", ["job_profile_id", "skill_id"], unique=True
    )


def downgrade() -> None:
    op.drop_index("uq_job_skills_profile_skill", table_name="job_skills")
    op.drop_index("ix_job_skills_skill_id", table_name="job_skills")
    op.drop_index("ix_job_skills_job_profile_id", table_name="job_skills")
    op.drop_table("job_skills")

    op.drop_index("ix_job_profiles_student_profile_id", table_name="job_profiles")
    op.drop_table("job_profiles")
