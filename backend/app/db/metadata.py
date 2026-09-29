"""Single import surface for Alembic autogenerate.

Importing this module guarantees every ORM class is registered on
``Base.metadata``. ``alembic/env.py`` imports it and nothing else.
"""

from app.db.base import Base
from app.models.admin import Admin
from app.models.application import Application
from app.models.interview_question import InterviewQuestion  # noqa: F401
from app.models.interview_topic import InterviewTopic  # noqa: F401
from app.models.job import Job
from app.models.job_profile import JobProfile  # noqa: F401
from app.models.job_skill import JobSkill  # noqa: F401
from app.models.match_analysis import MatchAnalysis  # noqa: F401
from app.models.preparation_item import PreparationItem  # noqa: F401
from app.models.preparation_plan import PreparationPlan  # noqa: F401
from app.models.skill import Skill, SkillAlias  # noqa: F401
from app.models.skill_gap import SkillGap  # noqa: F401
from app.models.skill_progress import SkillProgress  # noqa: F401
from app.models.skill_relation import SkillRelation  # noqa: F401
from app.models.student_profile import StudentProfile  # noqa: F401
from app.models.student_skill import StudentSkill  # noqa: F401

__all__ = ["Base", "Admin", "Application", "Job"]

target_metadata = Base.metadata
