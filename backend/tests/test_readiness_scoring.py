"""Unit tests for the deterministic readiness scoring/classification module
(no database)."""

from app.models.enums import JobRequirementType, SkillGapImportance, SkillGapType
from app.services.readiness_scoring import (
    classify_job_skills,
    compute_readiness,
    coverage_ratio,
    experience_alignment,
    years_from_label,
)

# Arbitrary but stable skill ids for these pure-function tests.
PYTHON, FASTAPI, POSTGRES, DOCKER, AWS, REDIS, DJANGO = range(1, 8)


def test_classify_reports_matched_when_student_has_the_skill():
    classifications = classify_job_skills(
        required_skill_ids={PYTHON},
        preferred_skill_ids=set(),
        student_skill_ids={PYTHON},
        related_lookup={},
    )
    assert classifications[0].gap_type == SkillGapType.MATCHED
    assert classifications[0].importance == SkillGapImportance.LOW


def test_classify_reports_missing_required_with_high_importance():
    classifications = classify_job_skills(
        required_skill_ids={DOCKER},
        preferred_skill_ids=set(),
        student_skill_ids=set(),
        related_lookup={},
    )
    assert classifications[0].gap_type == SkillGapType.MISSING_REQUIRED
    assert classifications[0].importance == SkillGapImportance.HIGH
    assert classifications[0].requirement_type == JobRequirementType.REQUIRED


def test_classify_reports_missing_preferred_with_medium_importance():
    classifications = classify_job_skills(
        required_skill_ids=set(),
        preferred_skill_ids={REDIS},
        student_skill_ids=set(),
        related_lookup={},
    )
    assert classifications[0].gap_type == SkillGapType.MISSING_PREFERRED
    assert classifications[0].importance == SkillGapImportance.MEDIUM


def test_classify_reports_related_only_when_an_explicit_relationship_exists():
    # Student has Django; job wants Python; Django -> Python is an explicit
    # seeded relationship.
    classifications = classify_job_skills(
        required_skill_ids={PYTHON},
        preferred_skill_ids=set(),
        student_skill_ids={DJANGO},
        related_lookup={PYTHON: {DJANGO}},
    )
    assert classifications[0].gap_type == SkillGapType.RELATED
    assert classifications[0].importance == SkillGapImportance.LOW
    assert classifications[0].related_to_skill_id == DJANGO


def test_classify_never_reports_related_without_an_explicit_relationship():
    # Student has Redis; job wants Docker; no relationship was seeded between
    # them, so this must be a plain miss, never a guessed "related".
    classifications = classify_job_skills(
        required_skill_ids={DOCKER},
        preferred_skill_ids=set(),
        student_skill_ids={REDIS},
        related_lookup={},
    )
    assert classifications[0].gap_type == SkillGapType.MISSING_REQUIRED


def test_related_skill_is_never_reported_as_matched():
    classifications = classify_job_skills(
        required_skill_ids={PYTHON},
        preferred_skill_ids=set(),
        student_skill_ids={DJANGO},
        related_lookup={PYTHON: {DJANGO}},
    )
    assert classifications[0].gap_type != SkillGapType.MATCHED


def test_classify_covers_required_and_preferred_together():
    classifications = classify_job_skills(
        required_skill_ids={PYTHON, FASTAPI, POSTGRES},
        preferred_skill_ids={DOCKER, AWS},
        student_skill_ids={PYTHON, FASTAPI, POSTGRES},
        related_lookup={},
    )
    by_skill = {c.skill_id: c for c in classifications}
    assert len(classifications) == 5
    assert by_skill[PYTHON].gap_type == SkillGapType.MATCHED
    assert by_skill[DOCKER].gap_type == SkillGapType.MISSING_PREFERRED
    assert by_skill[AWS].requirement_type == JobRequirementType.PREFERRED


def test_coverage_ratio_is_full_when_nothing_is_required():
    assert coverage_ratio(0, 0) == 1.0


def test_coverage_ratio_basic_fraction():
    assert coverage_ratio(3, 5) == 0.6


def test_years_from_label_parses_all_three_canonical_formats():
    assert years_from_label("3-5 years") == 3
    assert years_from_label("5+ years") == 5
    assert years_from_label("3 years") == 3
    assert years_from_label(None) is None
    assert years_from_label("no digits here") is None


def test_experience_alignment_full_score_when_job_has_no_requirement():
    alignment = experience_alignment(None, student_years=0)
    assert alignment.score == 1.0


def test_experience_alignment_full_score_when_student_meets_or_exceeds():
    alignment = experience_alignment("3 years", student_years=5)
    assert alignment.score == 1.0


def test_experience_alignment_partial_score_when_student_has_less():
    alignment = experience_alignment("4 years", student_years=2)
    assert alignment.score == 0.5


def test_experience_alignment_zero_when_no_evidence_detected():
    alignment = experience_alignment("3 years", student_years=None)
    assert alignment.score == 0.0
    assert "3 years" in alignment.explanation


def test_compute_readiness_is_full_when_every_component_is_full():
    score = compute_readiness(
        required_coverage=1.0, preferred_coverage=1.0, experience_score=1.0, text_similarity_score=1.0
    )
    assert score == 100.0


def test_compute_readiness_is_zero_when_every_component_is_zero():
    score = compute_readiness(
        required_coverage=0.0, preferred_coverage=0.0, experience_score=0.0, text_similarity_score=0.0
    )
    assert score == 0.0


def test_compute_readiness_weights_required_skills_most_heavily():
    only_required = compute_readiness(
        required_coverage=1.0, preferred_coverage=0.0, experience_score=0.0, text_similarity_score=0.0
    )
    only_preferred = compute_readiness(
        required_coverage=0.0, preferred_coverage=1.0, experience_score=0.0, text_similarity_score=0.0
    )
    assert only_required > only_preferred


def test_compute_readiness_matches_the_documented_formula():
    score = compute_readiness(
        required_coverage=0.6, preferred_coverage=0.5, experience_score=0.5, text_similarity_score=0.4
    )
    expected = round((0.6 * 0.45 + 0.5 * 0.15 + 0.5 * 0.20 + 0.4 * 0.20) * 100, 1)
    assert score == expected
