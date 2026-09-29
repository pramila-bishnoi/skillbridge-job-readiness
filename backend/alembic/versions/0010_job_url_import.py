"""Add job-URL-import traceability fields to job_profiles.

Revision ID: 0010
Revises: 0009

"Import from Job URL" (Analyze a Job): a student can paste a public
job-posting URL instead of the full description text. This adds the fields
that flow only need for such an import to be traceable back to its source —
all nullable, so a pasted description (the existing, still-primary path)
leaves them ``NULL``:

* ``source_url`` — the fetched page's final URL (after any redirects).
* ``location`` / ``employment_type_text`` / ``compensation_text`` /
  ``posted_date_text`` — best-effort structured fields (from schema.org
  JobPosting JSON-LD when present), stored as plain strings and never
  re-parsed into a stricter type.

No change to any existing column, and no change to how ``description`` is
analyzed (services/job_analysis.py, services/skill_normalization.py) — the
imported description flows through the exact same Phase 3 pipeline a pasted
one does.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("job_profiles", sa.Column("source_url", sa.String(length=2048), nullable=True))
    op.add_column("job_profiles", sa.Column("location", sa.String(length=200), nullable=True))
    op.add_column(
        "job_profiles", sa.Column("employment_type_text", sa.String(length=100), nullable=True)
    )
    op.add_column(
        "job_profiles", sa.Column("compensation_text", sa.String(length=200), nullable=True)
    )
    op.add_column(
        "job_profiles", sa.Column("posted_date_text", sa.String(length=100), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("job_profiles", "posted_date_text")
    op.drop_column("job_profiles", "compensation_text")
    op.drop_column("job_profiles", "employment_type_text")
    op.drop_column("job_profiles", "location")
    op.drop_column("job_profiles", "source_url")
