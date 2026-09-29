"""Interview-topic/question persistence (Phase 6)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.interview_question import InterviewQuestion
from app.models.interview_topic import InterviewTopic
from app.services.interview_prep_guidance import GeneratedTopic


class InterviewTopicRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_for_job(self, student_profile_id: int, job_profile_id: int) -> list[InterviewTopic]:
        stmt = (
            select(InterviewTopic)
            .options(joinedload(InterviewTopic.questions), joinedload(InterviewTopic.skill))
            .where(
                InterviewTopic.student_profile_id == student_profile_id,
                InterviewTopic.job_profile_id == job_profile_id,
            )
            .order_by(InterviewTopic.id)
        )
        return list(self.db.execute(stmt).unique().scalars().all())

    def replace_for_job(
        self,
        student_profile_id: int,
        job_profile_id: int,
        match_analysis_id: int,
        generated_topics: list[GeneratedTopic],
    ) -> None:
        """Deletes every existing topic (and its questions, via cascade) for
        this (student, job) pair and reinserts freshly generated ones.

        A full replace, not Phase 5's per-row merge: a project topic has no
        stable identity to merge against across a resume edit the way a
        skill gap does (skill_id), so instead of a fragile content-matching
        merge, a completed question's status is carried forward only when
        the newly generated question text is byte-identical to an existing
        completed one. Since generation is a pure function of the job
        skills, the student's gaps, and the exact projects text, an
        unrelated change elsewhere naturally leaves matching questions'
        text — and therefore their completed status — untouched.
        """
        existing_topics = self.list_for_job(student_profile_id, job_profile_id)
        completed_question_texts = {
            question.question
            for topic in existing_topics
            for question in topic.questions
            if question.completed
        }
        for topic in existing_topics:
            self.db.delete(topic)
        self.db.flush()

        for generated in generated_topics:
            topic = InterviewTopic(
                student_profile_id=student_profile_id,
                job_profile_id=job_profile_id,
                match_analysis_id=match_analysis_id,
                category=generated.category,
                skill_id=generated.skill_id,
                source_evidence=generated.source_evidence,
                reason=generated.reason,
            )
            self.db.add(topic)
            self.db.flush()
            for question in generated.questions:
                self.db.add(
                    InterviewQuestion(
                        interview_topic_id=topic.id,
                        question=question.text,
                        difficulty=question.difficulty,
                        completed=question.text in completed_question_texts,
                    )
                )
        self.db.flush()


class InterviewQuestionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id_for_job(
        self, student_profile_id: int, job_profile_id: int, question_id: int
    ) -> InterviewQuestion | None:
        stmt = (
            select(InterviewQuestion)
            .join(InterviewTopic, InterviewQuestion.interview_topic_id == InterviewTopic.id)
            .where(
                InterviewQuestion.id == question_id,
                InterviewTopic.student_profile_id == student_profile_id,
                InterviewTopic.job_profile_id == job_profile_id,
            )
        )
        return self.db.execute(stmt).scalar_one_or_none()
