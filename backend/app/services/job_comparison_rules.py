"""Deterministic job-comparison set operations (Phase 7).

Pure set math over already-computed Phase 4 data — no new scoring, no new
skill classification. A skill counts as "matched" for a job only when its
``SkillGap.gap_type`` is ``MATCHED``; every other gap type (missing-required,
missing-preferred, related) counts as "missing" here, the same posture
Phase 5/6 already take — a related skill is still something to prepare for,
never treated as satisfying the requirement.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class JobSkillSets:
    job_profile_id: int
    matched: frozenset[str]
    missing: frozenset[str]

    @property
    def considered(self) -> frozenset[str]:
        """Every skill this job cares about, required or preferred."""
        return self.matched | self.missing


@dataclass(frozen=True)
class ComparisonSets:
    common_skills: frozenset[str]
    common_missing_skills: frozenset[str]
    unique_missing_skills: dict[int, frozenset[str]]


def compare(job_sets: list[JobSkillSets]) -> ComparisonSets:
    """``common_skills``: every skill *every* compared job cares about.
    ``common_missing_skills``: a gap in *every* compared job — the highest
    leverage thing to fix, since closing it helps every role at once.
    ``unique_missing_skills``: per job, a gap that is NOT shared by all the
    others — specific to catching up for that one role."""
    if not job_sets:
        return ComparisonSets(frozenset(), frozenset(), {})

    common_skills = job_sets[0].considered
    common_missing = job_sets[0].missing
    for job_set in job_sets[1:]:
        common_skills = common_skills & job_set.considered
        common_missing = common_missing & job_set.missing

    unique_missing = {
        job_set.job_profile_id: job_set.missing - common_missing for job_set in job_sets
    }
    return ComparisonSets(
        common_skills=common_skills,
        common_missing_skills=common_missing,
        unique_missing_skills=unique_missing,
    )
