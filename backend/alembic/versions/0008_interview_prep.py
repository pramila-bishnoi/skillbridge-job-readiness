"""Add interview topics and their generated interview questions.

Revision ID: 0008
Revises: 0007

Phase 6 (Personalized Interview Preparation):

* ``interview_topics`` — one row per generating signal (a job skill the
  student matched or is missing, a project line quoted from their profile,
  or a generic role prompt), linked to the student, the job, and the
  readiness analysis it was generated from.
* ``interview_questions`` — one or more generated questions per topic, each
  with its own difficulty and a student-tracked ``completed`` flag.

No seed data — question text is generated at request time from templates in
``app/services/interview_prep_guidance.py``, not stored reference data.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INTERVIEW_CATEGORIES = ("TECHNICAL", "SKILL_GAP", "RESUME_PROJECT", "ROLE_CONCEPT")
INTERVIEW_DIFFICULTIES = ("EASY", "MEDIUM", "HARD")


def upgrade() -> None:
    # ------------------------------------------------------- interview_topics --
    op.create_table(
        "interview_topics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_profile_id", sa.Integer(), nullable=False),
        sa.Column("job_profile_id", sa.Integer(), nullable=False),
        sa.Column("match_analysis_id", sa.Integer(), nullable=False),
        sa.Column(
            "category",
            sa.Enum(*INTERVIEW_CATEGORIES, name="interviewcategory", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column("skill_id", sa.Integer(), nullable=True),
        sa.Column("source_evidence", sa.String(length=500), nullable=True),
        sa.Column("reason", sa.String(length=300), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["student_profile_id"],
            ["student_profiles.id"],
            name="fk_interview_topics_student_profile_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["job_profile_id"],
            ["job_profiles.id"],
            name="fk_interview_topics_job_profile_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["match_analysis_id"],
            ["match_analyses.id"],
            name="fk_interview_topics_match_analysis_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["skill_id"], ["skills.id"], name="fk_interview_topics_skill_id", ondelete="SET NULL"
        ),
    )
    op.create_index(
        "ix_interview_topics_student_profile_id", "interview_topics", ["student_profile_id"]
    )
    op.create_index("ix_interview_topics_job_profile_id", "interview_topics", ["job_profile_id"])
    op.create_index(
        "ix_interview_topics_match_analysis_id", "interview_topics", ["match_analysis_id"]
    )
    op.create_index("ix_interview_topics_skill_id", "interview_topics", ["skill_id"])
    op.create_index(
        "ix_interview_topics_student_job", "interview_topics", ["student_profile_id", "job_profile_id"]
    )

    # ---------------------------------------------------- interview_questions --
    op.create_table(
        "interview_questions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("interview_topic_id", sa.Integer(), nullable=False),
        sa.Column("question", sa.String(length=500), nullable=False),
        sa.Column(
            "difficulty",
            sa.Enum(*INTERVIEW_DIFFICULTIES, name="interviewdifficulty", native_enum=False, length=10),
            nullable=False,
        ),
        sa.Column("completed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["interview_topic_id"],
            ["interview_topics.id"],
            name="fk_interview_questions_interview_topic_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_interview_questions_interview_topic_id", "interview_questions", ["interview_topic_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_interview_questions_interview_topic_id", table_name="interview_questions")
    op.drop_table("interview_questions")

    op.drop_index("ix_interview_topics_student_job", table_name="interview_topics")
    op.drop_index("ix_interview_topics_skill_id", table_name="interview_topics")
    op.drop_index("ix_interview_topics_match_analysis_id", table_name="interview_topics")
    op.drop_index("ix_interview_topics_job_profile_id", table_name="interview_topics")
    op.drop_index("ix_interview_topics_student_profile_id", table_name="interview_topics")
    op.drop_table("interview_topics")
