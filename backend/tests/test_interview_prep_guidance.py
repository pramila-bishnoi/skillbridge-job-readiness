"""Unit tests for the deterministic interview-topic/question templates (no database)."""

from app.models.enums import (
    InterviewCategory,
    InterviewDifficulty,
    JobRequirementType,
    SkillGapType,
)
from app.services.interview_prep_guidance import (
    MAX_PROJECT_QUESTIONS,
    project_topics,
    role_concept_topics,
    skill_gap_topic,
    technical_topic,
)


def test_technical_topic_for_a_required_matched_skill_is_hard():
    topic = technical_topic(
        skill_id=1, skill_name="FastAPI", requirement_type=JobRequirementType.REQUIRED
    )
    assert topic.category == InterviewCategory.TECHNICAL
    assert topic.questions[0].difficulty == InterviewDifficulty.HARD
    assert "FastAPI" in topic.questions[0].text
    assert "FastAPI" in topic.reason
    assert "required" in topic.reason


def test_technical_topic_for_a_preferred_matched_skill_is_medium():
    topic = technical_topic(
        skill_id=1, skill_name="Git", requirement_type=JobRequirementType.PREFERRED
    )
    assert topic.questions[0].difficulty == InterviewDifficulty.MEDIUM
    assert "preferred" in topic.reason


def test_skill_gap_topic_for_missing_required_is_medium():
    topic = skill_gap_topic(
        skill_id=2,
        skill_name="Docker",
        gap_type=SkillGapType.MISSING_REQUIRED,
        requirement_type=JobRequirementType.REQUIRED,
        related_to_skill_name=None,
    )
    assert topic.category == InterviewCategory.SKILL_GAP
    assert topic.questions[0].difficulty == InterviewDifficulty.MEDIUM
    assert "Docker" in topic.questions[0].text
    assert "not found" in topic.reason


def test_skill_gap_topic_for_missing_preferred_is_easy():
    topic = skill_gap_topic(
        skill_id=3,
        skill_name="Redis",
        gap_type=SkillGapType.MISSING_PREFERRED,
        requirement_type=JobRequirementType.PREFERRED,
        related_to_skill_name=None,
    )
    assert topic.questions[0].difficulty == InterviewDifficulty.EASY


def test_skill_gap_topic_for_related_names_the_related_skill():
    topic = skill_gap_topic(
        skill_id=4,
        skill_name="Python",
        gap_type=SkillGapType.RELATED,
        requirement_type=JobRequirementType.REQUIRED,
        related_to_skill_name="Django",
    )
    assert topic.questions[0].difficulty == InterviewDifficulty.EASY
    assert "Django" in topic.questions[0].text
    assert "Django" in topic.reason


def test_project_topics_quotes_the_project_line_verbatim():
    topics = project_topics("Built an ESP32-based home automation system using MQTT.")
    assert len(topics) == 1
    topic = topics[0]
    assert topic.category == InterviewCategory.RESUME_PROJECT
    assert "ESP32" in topic.questions[0].text
    assert topic.source_evidence == "Built an ESP32-based home automation system using MQTT."
    # Nothing about the project is invented beyond the quoted line.
    assert "MQTT" not in topic.reason


def test_project_topics_splits_on_lines_and_skips_blank_lines():
    text = "Line one project.\n\n  \nLine two project.\n"
    topics = project_topics(text)
    assert [t.source_evidence for t in topics] == ["Line one project.", "Line two project."]


def test_project_topics_caps_at_max_project_questions():
    text = "\n".join(f"Project {i}" for i in range(MAX_PROJECT_QUESTIONS + 5))
    topics = project_topics(text)
    assert len(topics) == MAX_PROJECT_QUESTIONS


def test_project_topics_returns_nothing_for_empty_or_none():
    assert project_topics(None) == []
    assert project_topics("") == []
    assert project_topics("   \n  ") == []


def test_role_concept_topics_are_parameterized_only_by_job_title():
    topics = role_concept_topics("Backend Engineer")
    assert len(topics) == 2
    assert all(t.category == InterviewCategory.ROLE_CONCEPT for t in topics)
    assert all("Backend Engineer" in t.questions[0].text for t in topics)
    assert all(t.questions[0].difficulty == InterviewDifficulty.EASY for t in topics)
