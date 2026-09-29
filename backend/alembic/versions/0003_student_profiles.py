"""Add SkillBridge student profiles and resume intelligence fields.

Revision ID: 0003
Revises: 0002
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "student_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("education", sa.Text(), nullable=True),
        sa.Column("skills", sa.Text(), nullable=True),
        sa.Column("projects", sa.Text(), nullable=True),
        sa.Column("experience", sa.Text(), nullable=True),
        sa.Column("resume_key", sa.String(length=500), nullable=True),
        sa.Column("resume_filename", sa.String(length=255), nullable=True),
        sa.Column("resume_text", sa.Text(), nullable=True),
        sa.Column("extracted_skills", sa.Text(), nullable=True),
        sa.Column("resume_uploaded", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_student_profiles_email", "student_profiles", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_student_profiles_email", table_name="student_profiles")
    op.drop_table("student_profiles")