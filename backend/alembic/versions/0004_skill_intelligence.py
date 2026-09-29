"""Add canonical skill catalog, aliases, and per-student normalized skill evidence.

Revision ID: 0004
Revises: 0003

Phase 2 (Skill Intelligence): replaces the Phase 1 hardcoded skill list
(previously ``services/skill_extraction.py``) with a maintainable
``skills``/``skill_aliases`` catalog, plus ``student_skills`` linking a
normalized skill back to the student who evidenced it and the exact text that
triggered the match. The seed data below is the same ``SKILL_CATALOG`` the
pytest fixture seeds (``app/core/skill_catalog.py``), so both paths seed one
catalog. ``student_profiles.extracted_skills`` (0003) is left in place but
unused — migrations are additive only (CLAUDE.md §7).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SKILL_MATCH_TYPES = ("CANONICAL_NAME", "ALIAS")


def upgrade() -> None:
    # --------------------------------------------------------------- skills --
    op.create_table(
        "skills",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("normalized_key", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_skills_normalized_key", "skills", ["normalized_key"], unique=True)

    # --------------------------------------------------------- skill_aliases --
    op.create_table(
        "skill_aliases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column("alias", sa.String(length=100), nullable=False),
        sa.Column("normalized_key", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["skill_id"], ["skills.id"], name="fk_skill_aliases_skill_id", ondelete="CASCADE"
        ),
    )
    op.create_index("ix_skill_aliases_skill_id", "skill_aliases", ["skill_id"])
    op.create_index("ix_skill_aliases_normalized_key", "skill_aliases", ["normalized_key"], unique=True)

    # -------------------------------------------------------- student_skills --
    op.create_table(
        "student_skills",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_profile_id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
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
            ["student_profile_id"],
            ["student_profiles.id"],
            name="fk_student_skills_student_profile_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["skill_id"], ["skills.id"], name="fk_student_skills_skill_id", ondelete="CASCADE"
        ),
    )
    op.create_index("ix_student_skills_student_profile_id", "student_skills", ["student_profile_id"])
    op.create_index("ix_student_skills_skill_id", "student_skills", ["skill_id"])
    op.create_index(
        "uq_student_skills_profile_skill",
        "student_skills",
        ["student_profile_id", "skill_id"],
        unique=True,
    )

    # ----------------------------------------------------- seed the catalog --
    # The tables are brand new in this same migration, so a plain insert (not
    # an upsert) is correct: this migration never runs against a non-empty
    # skills table.
    from app.core.skill_catalog import SKILL_CATALOG, normalize_key

    skills_table = sa.table(
        "skills",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("normalized_key", sa.String),
        sa.column("category", sa.String),
        sa.column("is_active", sa.Boolean),
    )
    aliases_table = sa.table(
        "skill_aliases",
        sa.column("skill_id", sa.Integer),
        sa.column("alias", sa.String),
        sa.column("normalized_key", sa.String),
    )

    connection = op.get_bind()
    connection.execute(
        sa.insert(skills_table),
        [
            {
                "name": seed.name,
                "normalized_key": normalize_key(seed.name),
                "category": seed.category,
                "is_active": True,
            }
            for seed in SKILL_CATALOG
        ],
    )
    name_to_id = dict(connection.execute(sa.select(skills_table.c.name, skills_table.c.id)).all())
    alias_rows = [
        {"skill_id": name_to_id[seed.name], "alias": alias, "normalized_key": normalize_key(alias)}
        for seed in SKILL_CATALOG
        for alias in seed.aliases
    ]
    if alias_rows:
        connection.execute(sa.insert(aliases_table), alias_rows)


def downgrade() -> None:
    op.drop_index("uq_student_skills_profile_skill", table_name="student_skills")
    op.drop_index("ix_student_skills_skill_id", table_name="student_skills")
    op.drop_index("ix_student_skills_student_profile_id", table_name="student_skills")
    op.drop_table("student_skills")

    op.drop_index("ix_skill_aliases_normalized_key", table_name="skill_aliases")
    op.drop_index("ix_skill_aliases_skill_id", table_name="skill_aliases")
    op.drop_table("skill_aliases")

    op.drop_index("ix_skills_normalized_key", table_name="skills")
    op.drop_table("skills")
