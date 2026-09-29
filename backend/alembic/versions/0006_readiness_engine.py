"""Add skill relationships, job-readiness analyses, and their skill-gap breakdown.

Revision ID: 0006
Revises: 0005

Phase 4 (Explainable Job Readiness + Skill-Gap Engine):

* ``skill_relations`` — an explicit, curated "related to" edge between two
  skills (``SKILL_RELATIONSHIPS`` in ``app/core/skill_catalog.py``), seeded
  here the same way migration 0004 seeded the skill catalog itself.
* ``match_analyses`` — one explainable readiness analysis per
  (student, job) pair, with every scoring component stored as its own
  column.
* ``skill_gaps`` — the per-skill breakdown (matched / missing / related)
  behind one analysis.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JOB_REQUIREMENT_TYPES = ("REQUIRED", "PREFERRED")
SKILL_GAP_TYPES = ("MATCHED", "MISSING_REQUIRED", "MISSING_PREFERRED", "RELATED")
SKILL_GAP_IMPORTANCE = ("HIGH", "MEDIUM", "LOW")


def upgrade() -> None:
    # ------------------------------------------------------- skill_relations --
    op.create_table(
        "skill_relations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column("related_skill_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["skill_id"], ["skills.id"], name="fk_skill_relations_skill_id", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["related_skill_id"],
            ["skills.id"],
            name="fk_skill_relations_related_skill_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_skill_relations_skill_id", "skill_relations", ["skill_id"])
    op.create_index("ix_skill_relations_related_skill_id", "skill_relations", ["related_skill_id"])
    op.create_index(
        "uq_skill_relations_pair", "skill_relations", ["skill_id", "related_skill_id"], unique=True
    )

    # ------------------------------------------------------- match_analyses --
    op.create_table(
        "match_analyses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_profile_id", sa.Integer(), nullable=False),
        sa.Column("job_profile_id", sa.Integer(), nullable=False),
        sa.Column("required_skill_coverage", sa.Float(), nullable=False),
        sa.Column("required_matched_count", sa.Integer(), nullable=False),
        sa.Column("required_total_count", sa.Integer(), nullable=False),
        sa.Column("preferred_skill_coverage", sa.Float(), nullable=False),
        sa.Column("preferred_matched_count", sa.Integer(), nullable=False),
        sa.Column("preferred_total_count", sa.Integer(), nullable=False),
        sa.Column("experience_score", sa.Float(), nullable=False),
        sa.Column("experience_evidence", sa.String(length=300), nullable=False),
        sa.Column("text_similarity_score", sa.Float(), nullable=False),
        sa.Column("text_similarity_terms", sa.String(length=500), nullable=True),
        sa.Column("readiness_score", sa.Float(), nullable=False),
        sa.Column("score_version", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["student_profile_id"],
            ["student_profiles.id"],
            name="fk_match_analyses_student_profile_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["job_profile_id"],
            ["job_profiles.id"],
            name="fk_match_analyses_job_profile_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_match_analyses_student_profile_id", "match_analyses", ["student_profile_id"])
    op.create_index("ix_match_analyses_job_profile_id", "match_analyses", ["job_profile_id"])
    op.create_index("ix_match_analyses_readiness_score", "match_analyses", ["readiness_score"])
    op.create_index(
        "uq_match_analyses_student_job",
        "match_analyses",
        ["student_profile_id", "job_profile_id"],
        unique=True,
    )

    # ------------------------------------------------------------ skill_gaps --
    op.create_table(
        "skill_gaps",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("match_analysis_id", sa.Integer(), nullable=False),
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
            "importance",
            sa.Enum(*SKILL_GAP_IMPORTANCE, name="skillgapimportance", native_enum=False, length=10),
            nullable=False,
        ),
        sa.Column("evidence", sa.String(length=300), nullable=False),
        sa.Column("related_to_skill_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["match_analysis_id"],
            ["match_analyses.id"],
            name="fk_skill_gaps_match_analysis_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["skill_id"], ["skills.id"], name="fk_skill_gaps_skill_id", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["related_to_skill_id"],
            ["skills.id"],
            name="fk_skill_gaps_related_to_skill_id",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_skill_gaps_match_analysis_id", "skill_gaps", ["match_analysis_id"])
    op.create_index("ix_skill_gaps_skill_id", "skill_gaps", ["skill_id"])
    op.create_index(
        "uq_skill_gaps_analysis_skill", "skill_gaps", ["match_analysis_id", "skill_id"], unique=True
    )

    # --------------------------------------------------- seed relationships --
    # skill_relations references skills.id, which already exists (migration
    # 0004); this migration only adds edges between rows that are already
    # there, so a plain lookup-then-insert is correct and this migration
    # never runs against a non-empty skill_relations table.
    from app.core.skill_catalog import SKILL_RELATIONSHIPS, normalize_key

    skills_table = sa.table(
        "skills", sa.column("id", sa.Integer), sa.column("normalized_key", sa.String)
    )
    relations_table = sa.table(
        "skill_relations", sa.column("skill_id", sa.Integer), sa.column("related_skill_id", sa.Integer)
    )

    connection = op.get_bind()
    id_by_key = dict(
        connection.execute(sa.select(skills_table.c.normalized_key, skills_table.c.id)).all()
    )
    rows: list[dict[str, int]] = []
    for name_a, name_b in SKILL_RELATIONSHIPS:
        id_a = id_by_key.get(normalize_key(name_a))
        id_b = id_by_key.get(normalize_key(name_b))
        if id_a is None or id_b is None:
            continue
        rows.append({"skill_id": id_a, "related_skill_id": id_b})
        rows.append({"skill_id": id_b, "related_skill_id": id_a})
    if rows:
        connection.execute(sa.insert(relations_table), rows)


def downgrade() -> None:
    op.drop_index("uq_skill_gaps_analysis_skill", table_name="skill_gaps")
    op.drop_index("ix_skill_gaps_skill_id", table_name="skill_gaps")
    op.drop_index("ix_skill_gaps_match_analysis_id", table_name="skill_gaps")
    op.drop_table("skill_gaps")

    op.drop_index("uq_match_analyses_student_job", table_name="match_analyses")
    op.drop_index("ix_match_analyses_readiness_score", table_name="match_analyses")
    op.drop_index("ix_match_analyses_job_profile_id", table_name="match_analyses")
    op.drop_index("ix_match_analyses_student_profile_id", table_name="match_analyses")
    op.drop_table("match_analyses")

    op.drop_index("uq_skill_relations_pair", table_name="skill_relations")
    op.drop_index("ix_skill_relations_related_skill_id", table_name="skill_relations")
    op.drop_index("ix_skill_relations_skill_id", table_name="skill_relations")
    op.drop_table("skill_relations")
