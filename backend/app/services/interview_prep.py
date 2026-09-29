"""Interview-preparation orchestration (Phase 6).

Turns one Phase 4 ``MatchAnalysis``'s ``SkillGap`` rows, plus the student's
own ``projects`` text and the job's title, into a generated set of
``InterviewTopic``/``InterviewQuestion`` rows. Does not touch
``services/readiness_scoring.py`` or ``services/preparation*.py`` at all —
skill classification is read from the existing ``SkillGap.gap_type``
(Phase 4), never recomputed.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import (
    InterviewPrepNotFoundError,
    InterviewQuestionNotFoundError,
    JobProfileNotFoundError,
    MatchAnalysisNotFoundError,
)
from app.models.enums import InterviewCategory, InterviewDifficulty, SkillGapType
from app.models.job_profile import JobProfile
from app.models.match_analysis import MatchAnalysis
from app.models.student_profile import StudentProfile
from app.repositories.interview_topics import InterviewQuestionRepository, InterviewTopicRepository
from app.repositories.job_profiles import JobProfileRepository
from app.repositories.match_analyses import MatchAnalysisRepository
from app.repositories.skill_gaps import SkillGapRepository
from app.schemas.interview_prep import InterviewPrepDetail, InterviewQuestionOut
from app.services.interview_prep_guidance import (
    GeneratedTopic,
    project_topics,
    role_concept_topics,
    skill_gap_topic,
    technical_topic,
)

_CATEGORY_ORDER = {
    InterviewCategory.TECHNICAL: 0,
    InterviewCategory.SKILL_GAP: 1,
    InterviewCategory.RESUME_PROJECT: 2,
    InterviewCategory.ROLE_CONCEPT: 3,
}
_DIFFICULTY_ORDER = {
    InterviewDifficulty.HARD: 0,
    InterviewDifficulty.MEDIUM: 1,
    InterviewDifficulty.EASY: 2,
}


class InterviewPrepService:
    def __init__(self, db: Session):
        self.db = db
        self.job_profiles = JobProfileRepository(db)
        self.match_analyses = MatchAnalysisRepository(db)
        self.skill_gaps = SkillGapRepository(db)
        self.topics = InterviewTopicRepository(db)
        self.questions = InterviewQuestionRepository(db)

    def generate(self, profile: StudentProfile, job_profile_id: int) -> InterviewPrepDetail:
        """Generate (or regenerate) interview prep from the job's latest
        readiness analysis. Safe to call again after the resume or job
        description changes and readiness has been rerun."""
        job_profile = self._get_owned_job_or_404(profile, job_profile_id)
        analysis = self._get_analysis_or_404(profile, job_profile)

        gap_rows = self.skill_gaps.list_for_analysis(analysis.id)  # every gap_type, including MATCHED
        generated: list[GeneratedTopic] = []
        for gap in gap_rows:
            if gap.gap_type == SkillGapType.MATCHED:
                generated.append(
                    technical_topic(
                        skill_id=gap.skill_id,
                        skill_name=gap.skill.name,
                        requirement_type=gap.requirement_type,
                    )
                )
            else:
                generated.append(
                    skill_gap_topic(
                        skill_id=gap.skill_id,
                        skill_name=gap.skill.name,
                        gap_type=gap.gap_type,
                        requirement_type=gap.requirement_type,
                        related_to_skill_name=gap.related_to_skill.name if gap.related_to_skill else None,
                    )
                )
        generated.extend(project_topics(profile.projects))
        generated.extend(role_concept_topics(job_profile.title))

        self.topics.replace_for_job(profile.id, job_profile.id, analysis.id, generated)
        self.db.commit()
        return self._to_detail(job_profile, analysis)

    def get_for_student(self, profile: StudentProfile, job_profile_id: int) -> InterviewPrepDetail:
        job_profile = self._get_owned_job_or_404(profile, job_profile_id)
        analysis = self._get_analysis_or_404(profile, job_profile)
        topics = self.topics.list_for_job(profile.id, job_profile.id)
        if not topics:
            raise InterviewPrepNotFoundError()
        return self._to_detail(job_profile, analysis)

    def update_question_completed(
        self, profile: StudentProfile, job_profile_id: int, question_id: int, completed: bool
    ) -> InterviewPrepDetail:
        job_profile = self._get_owned_job_or_404(profile, job_profile_id)
        analysis = self._get_analysis_or_404(profile, job_profile)

        question = self.questions.get_by_id_for_job(profile.id, job_profile.id, question_id)
        if question is None:
            raise InterviewQuestionNotFoundError()

        question.completed = completed
        self.db.commit()
        return self._to_detail(job_profile, analysis)

    # ------------------------------------------------------------ internals --
    def _get_owned_job_or_404(self, profile: StudentProfile, job_profile_id: int) -> JobProfile:
        job_profile = self.job_profiles.get_by_id(job_profile_id)
        if job_profile is None or job_profile.student_profile_id != profile.id:
            raise JobProfileNotFoundError()
        return job_profile

    def _get_analysis_or_404(self, profile: StudentProfile, job_profile: JobProfile) -> MatchAnalysis:
        analysis = self.match_analyses.get_by_student_and_job(profile.id, job_profile.id)
        if analysis is None:
            raise MatchAnalysisNotFoundError()
        return analysis

    def _to_detail(self, job_profile: JobProfile, analysis: MatchAnalysis) -> InterviewPrepDetail:
        topics = self.topics.list_for_job(job_profile.student_profile_id, job_profile.id)
        questions: list[InterviewQuestionOut] = [
            InterviewQuestionOut(
                id=question.id,
                question=question.question,
                category=topic.category,
                related_skill_name=topic.skill.name if topic.skill else None,
                difficulty=question.difficulty,
                reason=topic.reason,
                completed=question.completed,
            )
            for topic in topics
            for question in topic.questions
        ]
        questions.sort(
            key=lambda q: (_CATEGORY_ORDER[q.category], _DIFFICULTY_ORDER[q.difficulty], q.id)
        )
        total = len(questions)
        completed = sum(1 for q in questions if q.completed)
        return InterviewPrepDetail(
            job_profile_id=job_profile.id,
            job_title=job_profile.title,
            match_analysis_id=analysis.id,
            total_questions=total,
            completed_questions=completed,
            progress_percent=round(completed / total * 100, 1) if total else 0.0,
            questions=questions,
        )
