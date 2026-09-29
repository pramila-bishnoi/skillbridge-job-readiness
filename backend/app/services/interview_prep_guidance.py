"""Deterministic, explainable interview-topic/question generation (Phase 6).

No external LLM anywhere in this module — every function is a fixed string
template parameterized only by plain values the caller already has:

* ``technical_topic`` / ``skill_gap_topic`` classify a job skill exactly the
  way Phase 4 already did (``SkillGap.gap_type``) — ``MATCHED`` becomes a
  depth-testing technical question, everything else becomes a
  fundamentals-level gap question. Nothing is reclassified here.
* ``project_topics`` never invents what a project involved: it splits the
  student's own ``projects`` text into lines and quotes each one verbatim
  into the question. A line about "ESP32" produces a question that says
  "ESP32", not a guess about what an ESP32 project might contain.
* ``role_concept_topics`` is a small fixed set of prompts parameterized only
  by the job title — no other assumption about the student or the job.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models.enums import (
    InterviewCategory,
    InterviewDifficulty,
    JobRequirementType,
    SkillGapType,
)

MAX_PROJECT_QUESTIONS = 5


@dataclass(frozen=True)
class GeneratedQuestion:
    text: str
    difficulty: InterviewDifficulty


@dataclass(frozen=True)
class GeneratedTopic:
    category: InterviewCategory
    skill_id: int | None
    source_evidence: str | None
    reason: str
    questions: list[GeneratedQuestion]


def technical_topic(
    *, skill_id: int, skill_name: str, requirement_type: JobRequirementType
) -> GeneratedTopic:
    """A job skill the student's profile already matches (``SkillGap.gap_type
    == MATCHED``) — the interview should test depth, not basics."""
    label = "required" if requirement_type == JobRequirementType.REQUIRED else "preferred"
    difficulty = (
        InterviewDifficulty.HARD
        if requirement_type == JobRequirementType.REQUIRED
        else InterviewDifficulty.MEDIUM
    )
    question = (
        f"You listed {skill_name} on your profile, and this role calls for it — walk me "
        f"through a specific way you've used {skill_name} and a trade-off you had to consider."
    )
    return GeneratedTopic(
        category=InterviewCategory.TECHNICAL,
        skill_id=skill_id,
        source_evidence=None,
        reason=f"{skill_name} is a {label} skill for this role, and your profile shows it.",
        questions=[GeneratedQuestion(question, difficulty)],
    )


def skill_gap_topic(
    *,
    skill_id: int,
    skill_name: str,
    gap_type: SkillGapType,
    requirement_type: JobRequirementType,
    related_to_skill_name: str | None,
) -> GeneratedTopic:
    """A job skill the student's profile is missing, or only related to
    (``SkillGap.gap_type`` MISSING_REQUIRED / MISSING_PREFERRED / RELATED)."""
    label = "required" if requirement_type == JobRequirementType.REQUIRED else "preferred"
    if gap_type == SkillGapType.RELATED and related_to_skill_name:
        question = (
            f"This role expects {skill_name}. You have experience with {related_to_skill_name} — "
            f"how would you apply that experience to get productive in {skill_name}?"
        )
        reason = (
            f"{skill_name} is {label} for this role. Your profile shows {related_to_skill_name}, "
            f"which is related but does not cover {skill_name} directly."
        )
        difficulty = InterviewDifficulty.EASY
    else:
        question = (
            f"This role expects familiarity with {skill_name}. What do you understand about "
            f"{skill_name} so far, and how would you approach learning it quickly?"
        )
        reason = f"{skill_name} is {label} for this role and was not found in your profile."
        difficulty = (
            InterviewDifficulty.MEDIUM
            if requirement_type == JobRequirementType.REQUIRED
            else InterviewDifficulty.EASY
        )
    return GeneratedTopic(
        category=InterviewCategory.SKILL_GAP,
        skill_id=skill_id,
        source_evidence=None,
        reason=reason,
        questions=[GeneratedQuestion(question, difficulty)],
    )


def project_topics(projects_text: str | None) -> list[GeneratedTopic]:
    """One topic per non-empty line of the student's own ``projects`` field,
    capped at ``MAX_PROJECT_QUESTIONS`` so a long paste can't flood the set.
    The line is quoted into the question verbatim — this function never adds
    a claim about the project that was not already in that text."""
    if not projects_text:
        return []
    lines = [line.strip() for line in projects_text.splitlines() if line.strip()]
    topics = []
    for line in lines[:MAX_PROJECT_QUESTIONS]:
        question = (
            f'Your profile mentions this project: "{line}" — walk me through what you built, '
            "the biggest technical challenge, and what you would do differently."
        )
        topics.append(
            GeneratedTopic(
                category=InterviewCategory.RESUME_PROJECT,
                skill_id=None,
                source_evidence=line,
                reason="Taken directly from the Projects section of your profile.",
                questions=[GeneratedQuestion(question, InterviewDifficulty.MEDIUM)],
            )
        )
    return topics


def role_concept_topics(job_title: str) -> list[GeneratedTopic]:
    """A small fixed set of general-fit prompts — the only input is the job
    title, so there is nothing here to fabricate about the student."""
    prompts = (
        f"What interests you about this {job_title} role specifically?",
        f"Walk me through how you'd approach your first 30 days in a {job_title} role.",
    )
    return [
        GeneratedTopic(
            category=InterviewCategory.ROLE_CONCEPT,
            skill_id=None,
            source_evidence=None,
            reason=f"A general question about your fit for the {job_title} role.",
            questions=[GeneratedQuestion(prompt, InterviewDifficulty.EASY)],
        )
        for prompt in prompts
    ]
