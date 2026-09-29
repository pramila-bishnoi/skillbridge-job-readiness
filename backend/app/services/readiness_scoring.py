"""Deterministic, explainable job-readiness scoring and skill-gap classification.

No external LLM/ML anywhere in this module. Two independent, inspectable
pieces, mirroring the "pure module + DB-aware orchestrator" split already
used by ``skill_normalization.py``/``student_profiles.py`` and
``job_analysis.py``/``job_profiles.py``:

1. ``classify_job_skills`` compares a job's required/preferred canonical
   skills against a student's canonical skills, using only exact skill-id
   membership and an explicit, pre-seeded relationship lookup (never a fuzzy
   or inferred one — see ``app/core/skill_catalog.py`` ``SKILL_RELATIONSHIPS``).
   A related skill is always reported as ``RELATED``, never ``MATCHED`` — it
   does not satisfy the requirement, it only narrows the gap.

2. ``compute_readiness`` combines four independently stored 0..1 components
   into one 0..100 score with fixed, documented weights (``WEIGHT_*`` below).
   Changing the formula means bumping ``SCORE_VERSION``, not silently
   reinterpreting old stored scores.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.models.enums import JobRequirementType, SkillGapImportance, SkillGapType

# ---------------------------------------------------------------------------
# Skill-gap classification
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SkillClassification:
    skill_id: int
    requirement_type: JobRequirementType
    gap_type: SkillGapType
    importance: SkillGapImportance
    evidence: str
    related_to_skill_id: int | None = None


_IMPORTANCE_BY_GAP_TYPE: dict[SkillGapType, SkillGapImportance] = {
    SkillGapType.MISSING_REQUIRED: SkillGapImportance.HIGH,
    SkillGapType.MISSING_PREFERRED: SkillGapImportance.MEDIUM,
    SkillGapType.RELATED: SkillGapImportance.LOW,
    # Not really "prioritized" (nothing to act on), but the column is
    # NOT NULL for schema simplicity — the UI never shows importance for a
    # matched skill.
    SkillGapType.MATCHED: SkillGapImportance.LOW,
}


def classify_job_skills(
    *,
    required_skill_ids: set[int],
    preferred_skill_ids: set[int],
    student_skill_ids: set[int],
    related_lookup: dict[int, set[int]],
) -> list[SkillClassification]:
    """One classification per job skill (required + preferred combined).

    ``related_lookup`` maps a job skill id to the set of *all* skill ids it is
    related to (``SkillRelationRepository.list_related``); intersecting that
    with ``student_skill_ids`` is what makes ``RELATED`` an explicit,
    seeded-data lookup rather than a runtime guess.
    """
    ordered = [(sid, JobRequirementType.REQUIRED) for sid in sorted(required_skill_ids)] + [
        (sid, JobRequirementType.PREFERRED) for sid in sorted(preferred_skill_ids)
    ]

    classifications: list[SkillClassification] = []
    for skill_id, requirement_type in ordered:
        if skill_id in student_skill_ids:
            classifications.append(
                SkillClassification(
                    skill_id=skill_id,
                    requirement_type=requirement_type,
                    gap_type=SkillGapType.MATCHED,
                    importance=_IMPORTANCE_BY_GAP_TYPE[SkillGapType.MATCHED],
                    evidence="Found in your normalized skills.",
                )
            )
            continue

        related_matches = related_lookup.get(skill_id, set()) & student_skill_ids
        if related_matches:
            # Deterministic tie-break: the lowest skill id, so the same input
            # always reports the same evidence.
            related_to_skill_id = min(related_matches)
            classifications.append(
                SkillClassification(
                    skill_id=skill_id,
                    requirement_type=requirement_type,
                    gap_type=SkillGapType.RELATED,
                    importance=_IMPORTANCE_BY_GAP_TYPE[SkillGapType.RELATED],
                    evidence=(
                        "A related skill in your profile does not fully satisfy this "
                        "requirement, but narrows the gap."
                    ),
                    related_to_skill_id=related_to_skill_id,
                )
            )
            continue

        gap_type = (
            SkillGapType.MISSING_REQUIRED
            if requirement_type == JobRequirementType.REQUIRED
            else SkillGapType.MISSING_PREFERRED
        )
        label = "required" if requirement_type == JobRequirementType.REQUIRED else "preferred"
        classifications.append(
            SkillClassification(
                skill_id=skill_id,
                requirement_type=requirement_type,
                gap_type=gap_type,
                importance=_IMPORTANCE_BY_GAP_TYPE[gap_type],
                evidence=f"Not found in your normalized skills; the job lists this as {label}.",
            )
        )
    return classifications


def coverage_ratio(matched: int, total: int) -> float:
    """1.0 (fully covered) when there is nothing to cover — a job with no
    preferred skills listed should never be penalised for "missing" them."""
    return 1.0 if total == 0 else matched / total


# ---------------------------------------------------------------------------
# Experience alignment
# ---------------------------------------------------------------------------

_YEARS_RE = re.compile(r"\d+")


def years_from_label(label: str | None) -> int | None:
    """Pulls the base number out of the canonical labels
    ``services/job_analysis.extract_experience`` produces ("3-5 years",
    "5+ years", "3 years") — reused for both the job's requirement and the
    student's own detected experience, so both sides are parsed identically."""
    if not label:
        return None
    match = _YEARS_RE.search(label)
    return int(match.group()) if match else None


@dataclass(frozen=True)
class ExperienceAlignment:
    score: float  # 0..1
    explanation: str


def experience_alignment(
    job_experience_required: str | None, student_years: int | None
) -> ExperienceAlignment:
    if job_experience_required is None:
        return ExperienceAlignment(1.0, "This job did not specify an experience requirement.")

    required_years = years_from_label(job_experience_required)
    if not required_years:
        return ExperienceAlignment(
            1.0, "This job did not specify a numeric experience requirement."
        )

    detected = student_years or 0
    score = min(detected / required_years, 1.0)
    explanation = (
        f"Detected {detected} year(s) of experience/project evidence in your profile "
        f"against a {job_experience_required} requirement."
    )
    return ExperienceAlignment(score, explanation)


# ---------------------------------------------------------------------------
# Final score
# ---------------------------------------------------------------------------

# Weights sum to 1.0. Required skills carry the most weight because a role's
# "Requirements" section is the strongest, most direct signal available;
# preferred skills, experience, and overall text similarity are each real but
# secondary signals. Changing these values changes SCORE_VERSION.
WEIGHT_REQUIRED = 0.45
WEIGHT_PREFERRED = 0.15
WEIGHT_EXPERIENCE = 0.20
WEIGHT_TEXT_SIMILARITY = 0.20
SCORE_VERSION = "v1"


def compute_readiness(
    *,
    required_coverage: float,
    preferred_coverage: float,
    experience_score: float,
    text_similarity_score: float,
) -> float:
    total = (
        required_coverage * WEIGHT_REQUIRED
        + preferred_coverage * WEIGHT_PREFERRED
        + experience_score * WEIGHT_EXPERIENCE
        + text_similarity_score * WEIGHT_TEXT_SIMILARITY
    )
    return round(total * 100, 1)
