"""Saved job-analysis orchestration.

Ties together the pure ``job_analysis`` segmentation/experience extraction,
the Phase 2 ``skill_normalization`` engine, and persistence — mirroring how
``services/student_profiles.py`` orchestrates resume upload + normalization.
Deliberately does not import or call anything from ``services/matching.py``:
job analysis stays independent of the ATS's resume-vs-job scoring engine.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import JobProfileNotFoundError
from app.models.enums import JobRequirementType
from app.models.job_profile import JobProfile
from app.models.job_skill import JobSkill
from app.models.skill import Skill
from app.models.student_profile import StudentProfile
from app.repositories.job_profiles import JobProfileRepository
from app.repositories.job_skills import JobSkillRepository
from app.repositories.skills import SkillRepository
from app.schemas.job_profile import (
    JobProfileCreate,
    JobProfileDetail,
    JobProfileSummary,
    JobRequirementSkillOut,
)
from app.services.job_analysis import extract_experience, segment_description
from app.services.skill_normalization import NormalizedSkillMatch, normalize_skills


def classify_required_and_preferred_skills(
    description: str, catalog: list[Skill]
) -> tuple[list[NormalizedSkillMatch], list[NormalizedSkillMatch]]:
    """Deterministic required/preferred skill classification for a job
    description — the Phase 3 analysis pipeline. Shared by ``JobProfileService``
    (which persists the result) and the job-URL-import preview (which does
    not), so the two paths can never drift apart."""
    segmented = segment_description(description)
    required_matches = normalize_skills(segmented.required_text, catalog)
    preferred_matches = normalize_skills(segmented.preferred_text, catalog)
    # A skill that (unusually) appears in both spans is reported once, as
    # required — required is the stronger, and clearer, claim.
    required_ids = {match.skill_id for match in required_matches}
    preferred_matches = [m for m in preferred_matches if m.skill_id not in required_ids]
    return required_matches, preferred_matches


class JobProfileService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = JobProfileRepository(db)
        self.job_skills = JobSkillRepository(db)
        self.skills = SkillRepository(db)

    def create(self, profile: StudentProfile, payload: JobProfileCreate) -> JobProfileDetail:
        job_profile = JobProfile(
            student_profile_id=profile.id,
            title=payload.title.strip(),
            company=payload.company.strip() if payload.company else None,
            description=payload.description,
            source_url=payload.source_url.strip() if payload.source_url else None,
            location=payload.location.strip() if payload.location else None,
            employment_type_text=payload.employment_type.strip() if payload.employment_type else None,
            compensation_text=payload.compensation.strip() if payload.compensation else None,
            posted_date_text=payload.posted_date.strip() if payload.posted_date else None,
        )
        self.repo.add(job_profile)
        self.db.commit()
        self.db.refresh(job_profile)

        self._analyze(job_profile)
        return self._to_detail(job_profile)

    def get_for_student(self, profile: StudentProfile, job_profile_id: int) -> JobProfileDetail:
        job_profile = self._get_owned_or_404(profile, job_profile_id)
        return self._to_detail(job_profile)

    def list_for_student(self, profile: StudentProfile) -> list[JobProfileSummary]:
        job_profiles = self.repo.list_for_student(profile.id)
        if not job_profiles:
            return []
        counts = self.job_skills.count_by_job([jp.id for jp in job_profiles])
        return [self._to_summary(jp, counts.get(jp.id, {})) for jp in job_profiles]

    def reanalyze_for_student(self, profile: StudentProfile, job_profile_id: int) -> JobProfileDetail:
        job_profile = self._get_owned_or_404(profile, job_profile_id)
        self._analyze(job_profile)
        self.db.refresh(job_profile)
        return self._to_detail(job_profile)

    # ------------------------------------------------------------ internals --
    def _analyze(self, job_profile: JobProfile) -> None:
        """Deterministic pipeline: segment -> normalize each span against the
        canonical catalog -> extract an experience requirement -> persist."""
        catalog = self.skills.list_catalog()
        required_matches, preferred_matches = classify_required_and_preferred_skills(
            job_profile.description, catalog
        )

        experience = extract_experience(job_profile.description)
        job_profile.experience_required = experience.required if experience else None
        job_profile.experience_evidence = experience.evidence if experience else None

        self.job_skills.replace_for_job(job_profile.id, required_matches, preferred_matches)
        self.db.commit()

    def _get_owned_or_404(self, profile: StudentProfile, job_profile_id: int) -> JobProfile:
        job_profile = self.repo.get_by_id(job_profile_id)
        # A job profile that exists but belongs to a different student reads
        # as "not found", the same posture as candidate tracking (README §18,
        # "a wrong email and an unknown code return an identical 404") — it
        # must not confirm that some other student's analysis exists.
        if job_profile is None or job_profile.student_profile_id != profile.id:
            raise JobProfileNotFoundError()
        return job_profile

    @staticmethod
    def _to_summary(job_profile: JobProfile, counts: dict[JobRequirementType, int]) -> JobProfileSummary:
        return JobProfileSummary(
            id=job_profile.id,
            title=job_profile.title,
            company=job_profile.company,
            experience_required=job_profile.experience_required,
            required_skill_count=counts.get(JobRequirementType.REQUIRED, 0),
            preferred_skill_count=counts.get(JobRequirementType.PREFERRED, 0),
            created_at=job_profile.created_at,
            updated_at=job_profile.updated_at,
        )

    def _to_detail(self, job_profile: JobProfile) -> JobProfileDetail:
        rows = self.job_skills.list_for_job(job_profile.id)
        required = [
            self._to_skill_out(row) for row in rows if row.requirement_type == JobRequirementType.REQUIRED
        ]
        preferred = [
            self._to_skill_out(row) for row in rows if row.requirement_type == JobRequirementType.PREFERRED
        ]
        return JobProfileDetail(
            id=job_profile.id,
            title=job_profile.title,
            company=job_profile.company,
            description=job_profile.description,
            experience_required=job_profile.experience_required,
            experience_evidence=job_profile.experience_evidence,
            required_skills=required,
            preferred_skills=preferred,
            source_url=job_profile.source_url,
            location=job_profile.location,
            employment_type=job_profile.employment_type_text,
            compensation=job_profile.compensation_text,
            posted_date=job_profile.posted_date_text,
            created_at=job_profile.created_at,
            updated_at=job_profile.updated_at,
        )

    @staticmethod
    def _to_skill_out(row: JobSkill) -> JobRequirementSkillOut:
        return JobRequirementSkillOut(
            skill_id=row.skill_id,
            name=row.skill.name,
            category=row.skill.category,
            matched_text=row.matched_text,
            match_type=row.match_type,
        )
