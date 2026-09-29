"""Job-readiness analysis orchestration (Phase 4).

Combines: Phase 2's canonical student skills, Phase 3's canonical job
skills/experience extraction, an explicit skill-relationship lookup, and the
legacy ATS's own TF-IDF/cosine engine (``services/matching.score_pair``,
reused unchanged, as one input among several — never the sole signal) into
one explainable ``MatchAnalysis`` + its ``SkillGap`` breakdown.

Deliberately does not modify ``services/matching.py`` or the ATS
``Job``/``Application`` models it operates on; this service only imports
``score_pair``, which already takes plain text and has no ATS-specific
coupling.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import JobProfileNotFoundError, MatchAnalysisNotFoundError
from app.models.enums import JobRequirementType, SkillGapType
from app.models.job_profile import JobProfile
from app.models.match_analysis import MatchAnalysis
from app.models.skill_gap import SkillGap
from app.models.student_profile import StudentProfile
from app.repositories.job_profiles import JobProfileRepository
from app.repositories.job_skills import JobSkillRepository
from app.repositories.match_analyses import MatchAnalysisRepository
from app.repositories.skill_gaps import SkillGapRepository
from app.repositories.skill_relations import SkillRelationRepository
from app.repositories.student_skills import StudentSkillRepository
from app.schemas.readiness import MatchAnalysisDetail, SkillGapOut
from app.services.job_analysis import extract_experience
from app.services.matching import score_pair
from app.services.readiness_scoring import (
    SCORE_VERSION,
    classify_job_skills,
    compute_readiness,
    coverage_ratio,
    experience_alignment,
    years_from_label,
)

_MISSING_TYPES = (SkillGapType.MISSING_REQUIRED, SkillGapType.MISSING_PREFERRED)
_GAP_TYPES = (SkillGapType.MISSING_REQUIRED, SkillGapType.MISSING_PREFERRED, SkillGapType.RELATED)


class ReadinessService:
    def __init__(self, db: Session):
        self.db = db
        self.job_profiles = JobProfileRepository(db)
        self.job_skills = JobSkillRepository(db)
        self.student_skills = StudentSkillRepository(db)
        self.skill_relations = SkillRelationRepository(db)
        self.match_analyses = MatchAnalysisRepository(db)
        self.skill_gaps = SkillGapRepository(db)

    def analyze(self, profile: StudentProfile, job_profile_id: int) -> MatchAnalysisDetail:
        """Compute (or recompute) the readiness analysis for this student
        against this saved job. Safe to call repeatedly — e.g. after the
        student uploads a new resume, or after the job description is
        re-analyzed — since it always overwrites the one existing row rather
        than adding another (see MatchAnalysisRepository.upsert)."""
        job_profile = self._get_owned_job_or_404(profile, job_profile_id)

        job_skill_rows = self.job_skills.list_for_job(job_profile.id)
        required_ids = {
            row.skill_id for row in job_skill_rows if row.requirement_type == JobRequirementType.REQUIRED
        }
        preferred_ids = {
            row.skill_id for row in job_skill_rows if row.requirement_type == JobRequirementType.PREFERRED
        }
        student_skill_ids = {row.skill_id for row in self.student_skills.list_for_profile(profile.id)}

        related_lookup = self.skill_relations.list_related(required_ids | preferred_ids)
        classifications = classify_job_skills(
            required_skill_ids=required_ids,
            preferred_skill_ids=preferred_ids,
            student_skill_ids=student_skill_ids,
            related_lookup=related_lookup,
        )

        required_matched = sum(
            1
            for c in classifications
            if c.requirement_type == JobRequirementType.REQUIRED and c.gap_type == SkillGapType.MATCHED
        )
        preferred_matched = sum(
            1
            for c in classifications
            if c.requirement_type == JobRequirementType.PREFERRED and c.gap_type == SkillGapType.MATCHED
        )
        required_coverage = coverage_ratio(required_matched, len(required_ids))
        preferred_coverage = coverage_ratio(preferred_matched, len(preferred_ids))

        # Text similarity: the legacy ATS's own pairwise TF-IDF/cosine engine,
        # reused as-is against the job description and a text snapshot of the
        # student's whole profile (not just the resume extract).
        candidate_text = _join_nonempty(
            profile.resume_text, profile.skills, profile.projects, profile.experience, profile.education
        )
        text_match = score_pair(job_profile.description, candidate_text)
        text_similarity_score = text_match.score / 100.0

        # Experience alignment: the same deterministic parser Phase 3 uses on
        # a job description is reused here on the student's own text, so
        # both sides produce directly comparable labels.
        student_experience_text = _join_nonempty(
            profile.resume_text, profile.experience, profile.projects
        )
        detected = extract_experience(student_experience_text)
        student_years = years_from_label(detected.required) if detected else None
        experience = experience_alignment(job_profile.experience_required, student_years)

        readiness_score = compute_readiness(
            required_coverage=required_coverage,
            preferred_coverage=preferred_coverage,
            experience_score=experience.score,
            text_similarity_score=text_similarity_score,
        )

        analysis = self.match_analyses.upsert(
            student_profile_id=profile.id,
            job_profile_id=job_profile.id,
            required_skill_coverage=round(required_coverage * 100, 1),
            required_matched_count=required_matched,
            required_total_count=len(required_ids),
            preferred_skill_coverage=round(preferred_coverage * 100, 1),
            preferred_matched_count=preferred_matched,
            preferred_total_count=len(preferred_ids),
            experience_score=round(experience.score * 100, 1),
            experience_evidence=experience.explanation,
            text_similarity_score=round(text_similarity_score * 100, 1),
            text_similarity_terms=text_match.terms or None,
            readiness_score=readiness_score,
            score_version=SCORE_VERSION,
        )
        self.skill_gaps.replace_for_analysis(analysis.id, classifications)
        self.db.commit()
        self.db.refresh(analysis)
        return self._to_detail(analysis, job_profile)

    def get_latest_for_student(self, profile: StudentProfile, job_profile_id: int) -> MatchAnalysisDetail:
        job_profile = self._get_owned_job_or_404(profile, job_profile_id)
        analysis = self._get_analysis_or_404(profile, job_profile)
        return self._to_detail(analysis, job_profile)

    def list_matched(self, profile: StudentProfile, job_profile_id: int) -> list[SkillGapOut]:
        analysis = self._require_analysis(profile, job_profile_id)
        rows = self.skill_gaps.list_for_analysis(analysis.id, gap_types=[SkillGapType.MATCHED])
        return [self._to_skill_gap_out(row) for row in rows]

    def list_missing(self, profile: StudentProfile, job_profile_id: int) -> list[SkillGapOut]:
        analysis = self._require_analysis(profile, job_profile_id)
        rows = self.skill_gaps.list_for_analysis(analysis.id, gap_types=list(_MISSING_TYPES))
        return [self._to_skill_gap_out(row) for row in rows]

    def list_gaps(self, profile: StudentProfile, job_profile_id: int) -> list[SkillGapOut]:
        analysis = self._require_analysis(profile, job_profile_id)
        rows = self.skill_gaps.list_for_analysis(analysis.id, gap_types=list(_GAP_TYPES))
        return [self._to_skill_gap_out(row) for row in rows]

    # ------------------------------------------------------------ internals --
    def _get_owned_job_or_404(self, profile: StudentProfile, job_profile_id: int) -> JobProfile:
        # Same "not found, not forbidden" posture as JobProfileService: a job
        # profile owned by a different student must not be distinguishable
        # from one that does not exist at all.
        job_profile = self.job_profiles.get_by_id(job_profile_id)
        if job_profile is None or job_profile.student_profile_id != profile.id:
            raise JobProfileNotFoundError()
        return job_profile

    def _get_analysis_or_404(self, profile: StudentProfile, job_profile: JobProfile) -> MatchAnalysis:
        analysis = self.match_analyses.get_by_student_and_job(profile.id, job_profile.id)
        if analysis is None:
            raise MatchAnalysisNotFoundError()
        return analysis

    def _require_analysis(self, profile: StudentProfile, job_profile_id: int) -> MatchAnalysis:
        job_profile = self._get_owned_job_or_404(profile, job_profile_id)
        return self._get_analysis_or_404(profile, job_profile)

    def _to_detail(self, analysis: MatchAnalysis, job_profile: JobProfile) -> MatchAnalysisDetail:
        rows = self.skill_gaps.list_for_analysis(analysis.id)
        matched = [self._to_skill_gap_out(r) for r in rows if r.gap_type == SkillGapType.MATCHED]
        missing = [self._to_skill_gap_out(r) for r in rows if r.gap_type in _MISSING_TYPES]
        gaps = [self._to_skill_gap_out(r) for r in rows if r.gap_type in _GAP_TYPES]
        return MatchAnalysisDetail(
            id=analysis.id,
            job_profile_id=job_profile.id,
            job_title=job_profile.title,
            readiness_score=analysis.readiness_score,
            score_version=analysis.score_version,
            required_skill_coverage=analysis.required_skill_coverage,
            required_matched_count=analysis.required_matched_count,
            required_total_count=analysis.required_total_count,
            preferred_skill_coverage=analysis.preferred_skill_coverage,
            preferred_matched_count=analysis.preferred_matched_count,
            preferred_total_count=analysis.preferred_total_count,
            experience_score=analysis.experience_score,
            experience_evidence=analysis.experience_evidence,
            text_similarity_score=analysis.text_similarity_score,
            text_similarity_terms=analysis.text_similarity_terms,
            matched_skills=matched,
            missing_skills=missing,
            skill_gaps=gaps,
            created_at=analysis.created_at,
            updated_at=analysis.updated_at,
        )

    @staticmethod
    def _to_skill_gap_out(row: SkillGap) -> SkillGapOut:
        return SkillGapOut(
            skill_id=row.skill_id,
            name=row.skill.name,
            category=row.skill.category,
            requirement_type=row.requirement_type,
            gap_type=row.gap_type,
            importance=row.importance,
            evidence=row.evidence,
            related_to_skill_name=row.related_to_skill.name if row.related_to_skill else None,
        )


def _join_nonempty(*parts: str | None) -> str:
    return " ".join(part for part in parts if part)
