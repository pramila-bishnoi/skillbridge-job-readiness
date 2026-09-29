"""Controlled vocabularies.

These enums are the single source of truth for the whole system. The database
stores their ``value`` strings, Pydantic validates against them, and
``frontend/src/types/api.ts`` mirrors them. Nothing anywhere should compare
against a bare string such as ``"interview"``.
"""

from __future__ import annotations

from enum import Enum


class EmploymentType(str, Enum):
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    CONTRACT = "CONTRACT"
    INTERNSHIP = "INTERNSHIP"


class ApplicationStatus(str, Enum):
    """The hiring pipeline.

        APPLIED -> SCREENING -> INTERVIEW -> SELECTED
        APPLIED | SCREENING | INTERVIEW -> REJECTED

    ``SELECTED`` and ``REJECTED`` are terminal. The transition table below is
    the *only* implementation of these rules in the codebase (project rule R3);
    the admin API, the UI and the tests all defer to ``can_transition``.
    """

    APPLIED = "APPLIED"
    SCREENING = "SCREENING"
    INTERVIEW = "INTERVIEW"
    SELECTED = "SELECTED"
    REJECTED = "REJECTED"

    @classmethod
    def allowed_transitions(cls) -> dict[ApplicationStatus, set[ApplicationStatus]]:
        return {
            cls.APPLIED: {cls.SCREENING, cls.REJECTED},
            cls.SCREENING: {cls.INTERVIEW, cls.REJECTED},
            cls.INTERVIEW: {cls.SELECTED, cls.REJECTED},
            cls.SELECTED: set(),
            cls.REJECTED: set(),
        }

    @classmethod
    def can_transition(cls, current: ApplicationStatus, target: ApplicationStatus) -> bool:
        if current == target:
            return False  # a no-op status change is treated as a client mistake
        return target in cls.allowed_transitions()[current]

    @classmethod
    def next_statuses(cls, current: ApplicationStatus) -> list[ApplicationStatus]:
        """Used by the admin UI to render only the legal next steps."""
        return sorted(cls.allowed_transitions()[current], key=lambda s: s.value)

    @property
    def is_terminal(self) -> bool:
        return self in {ApplicationStatus.SELECTED, ApplicationStatus.REJECTED}


class SkillMatchType(str, Enum):
    """How a normalized skill was identified in resume text.

    Stored on ``student_skills`` alongside the matched substring so the student
    (and any future readiness feature) can see *why* a skill was detected —
    project rule R2/R3's "one source of truth" pattern applied to skill
    evidence instead of the hiring pipeline.
    """

    CANONICAL_NAME = "CANONICAL_NAME"  # the skill's own name appeared in the text
    ALIAS = "ALIAS"  # a seeded synonym (e.g. "Postgres") appeared instead


class JobRequirementType(str, Enum):
    """Whether a skill detected in a saved job description was found in the
    description's "required" text or its "preferred" text (Phase 3: Job
    Description Intelligence). See ``services/job_analysis.py``."""

    REQUIRED = "REQUIRED"
    PREFERRED = "PREFERRED"


class SkillGapType(str, Enum):
    """How one job skill compares to a student's normalized skills, produced
    by ``services/readiness_scoring.classify_job_skills`` (Phase 4).

    ``RELATED`` is reported only when an explicit row exists in
    ``skill_relations`` (seeded from ``SKILL_RELATIONSHIPS`` in
    ``app/core/skill_catalog.py``) — never inferred. A related skill is never
    treated as satisfying the requirement; it stays a gap, just a smaller one.
    """

    MATCHED = "MATCHED"
    MISSING_REQUIRED = "MISSING_REQUIRED"
    MISSING_PREFERRED = "MISSING_PREFERRED"
    RELATED = "RELATED"


class SkillGapImportance(str, Enum):
    """Deterministic priority for a non-matched skill: missing-and-required
    skills outrank missing-and-preferred, which outrank a related-but-not-met
    skill. Applied uniformly by ``services/readiness_scoring._importance_for``
    — never hand-tuned per job or per student."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class PreparationItemStatus(str, Enum):
    """A student's own self-reported progress on one preparation item
    (Phase 5). Never derived automatically — only ``PATCH .../items/{id}``
    changes it, and regenerating the plan preserves whatever value is here
    for a skill that is still a gap (``PreparationItemRepository.replace_for_plan``)."""

    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class InterviewCategory(str, Enum):
    """Why one interview topic was generated (Phase 6). Each value maps to
    exactly one generator in ``services/interview_prep_guidance.py``:
    ``TECHNICAL`` and ``SKILL_GAP`` come from a job skill's Phase 4
    ``SkillGap.gap_type`` (MATCHED -> technical, everything else -> gap);
    ``RESUME_PROJECT`` comes from the student's own ``projects`` text,
    quoted verbatim; ``ROLE_CONCEPT`` is a small fixed set of prompts
    parameterized only by the job title."""

    TECHNICAL = "TECHNICAL"
    SKILL_GAP = "SKILL_GAP"
    RESUME_PROJECT = "RESUME_PROJECT"
    ROLE_CONCEPT = "ROLE_CONCEPT"


class InterviewDifficulty(str, Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class SkillProgressStatus(str, Enum):
    """A student's own self-reported learning progress on one canonical
    skill (Phase 7) — independent of whether that skill is on their resume
    at all. Never derived from resume text, a readiness analysis, or a
    preparation/interview item; only ``PATCH .../skill-progress/{skill_id}``
    changes it."""

    NOT_STARTED = "NOT_STARTED"
    LEARNING = "LEARNING"
    PRACTICED = "PRACTICED"
    CONFIDENT = "CONFIDENT"


# Reference vocabularies for seed data, filter dropdowns and validation help.
# Departments/locations stay free-text columns (a startup adds new ones without
# a migration) but the UI offers these as the curated list.
DEPARTMENTS: tuple[str, ...] = (
    "Engineering",
    "Human Resources",
    "Finance",
    "Sales",
    "Marketing",
    "Operations",
    "Support",
    "Design",
    "Data",
)

LOCATIONS: tuple[str, ...] = (
    "Delhi NCR",
    "Bengaluru",
    "Mumbai",
    "Hyderabad",
    "Pune",
    "Remote",
)
