"""Interview-preparation API contracts (Phase 6)."""

from __future__ import annotations

from pydantic import BaseModel

from app.models.enums import InterviewCategory, InterviewDifficulty


class InterviewQuestionOut(BaseModel):
    id: int
    question: str
    category: InterviewCategory
    related_skill_name: str | None
    difficulty: InterviewDifficulty
    reason: str
    completed: bool


class InterviewQuestionCompletedUpdate(BaseModel):
    completed: bool


class InterviewPrepDetail(BaseModel):
    job_profile_id: int
    job_title: str
    match_analysis_id: int

    total_questions: int
    completed_questions: int
    progress_percent: float

    questions: list[InterviewQuestionOut]
