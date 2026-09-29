"""Store resume text extract and TF-IDF match score on applications.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-28
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("applications", sa.Column("resume_text", sa.Text(), nullable=True))
    op.add_column("applications", sa.Column("match_score", sa.Float(), nullable=True))
    op.add_column("applications", sa.Column("match_terms", sa.String(length=500), nullable=True))
    op.create_index("ix_applications_match_score", "applications", ["match_score"])


def downgrade() -> None:
    op.drop_index("ix_applications_match_score", table_name="applications")
    op.drop_column("applications", "match_terms")
    op.drop_column("applications", "match_score")
    op.drop_column("applications", "resume_text")
