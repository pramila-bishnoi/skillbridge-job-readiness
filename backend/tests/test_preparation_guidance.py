"""Unit tests for the deterministic preparation guidance templates (no database)."""

from app.models.enums import SkillGapType
from app.services.preparation_guidance import learning_focus_for, reason_for


def test_learning_focus_returns_the_catalog_entry_for_a_known_skill():
    assert "Dockerfile" in learning_focus_for("Docker")
    assert "EC2" in learning_focus_for("AWS")


def test_learning_focus_falls_back_deterministically_for_an_unknown_skill():
    focus = learning_focus_for("Nonexistent Skill")
    assert "Nonexistent Skill" in focus
    # Same input, same output — no randomness, no external call.
    assert focus == learning_focus_for("Nonexistent Skill")


def test_reason_for_missing_required_names_the_job_and_skill():
    reason = reason_for(
        gap_type=SkillGapType.MISSING_REQUIRED,
        job_title="Backend Engineer",
        skill_name="Docker",
        related_to_skill_name=None,
    )
    assert "Backend Engineer" in reason
    assert "Docker" in reason
    assert "required" in reason


def test_reason_for_missing_preferred_names_the_job_and_skill():
    reason = reason_for(
        gap_type=SkillGapType.MISSING_PREFERRED,
        job_title="Backend Engineer",
        skill_name="Redis",
        related_to_skill_name=None,
    )
    assert "preferred" in reason
    assert "Redis" in reason


def test_reason_for_related_names_the_related_skill_when_present():
    reason = reason_for(
        gap_type=SkillGapType.RELATED,
        job_title="Backend Engineer",
        skill_name="Python",
        related_to_skill_name="Django",
    )
    assert "Django" in reason
    assert "Python" in reason
    assert "does not fully satisfy" in reason


def test_reason_for_related_degrades_gracefully_without_a_related_skill_name():
    reason = reason_for(
        gap_type=SkillGapType.RELATED,
        job_title="Backend Engineer",
        skill_name="Python",
        related_to_skill_name=None,
    )
    assert "Python" in reason
