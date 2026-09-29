"""Job-URL-import orchestration ("Import from Job URL" on Analyze a Job).

Flow: validate + SSRF-check the URL (``job_url_security``) -> fetch the page,
bounded and without executing any JavaScript (``job_url_fetch``) -> extract
structured fields, JSON-LD first then a deterministic HTML fallback
(``job_url_extraction``) -> build a *preview* using the existing, unmodified
Phase 3 pipeline (``job_analysis.extract_experience`` and
``job_profiles.classify_required_and_preferred_skills``) so a student can
check the result before anything is saved.

This module never writes to the database. Saving still goes through the
existing ``POST /student/jobs`` (``JobProfileService.create``, now accepting
the extra optional fields this preview surfaces) once the student confirms —
the same Phase 3 analysis a pasted description gets, not a second code path.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.exceptions import JobUrlExtractionFailedError
from app.models.skill import Skill
from app.repositories.skills import SkillRepository
from app.schemas.job_profile import JobRequirementSkillOut
from app.services.job_analysis import extract_experience
from app.services.job_profiles import classify_required_and_preferred_skills
from app.services.job_url_extraction import ExtractedJobPosting, extract_job_posting
from app.services.job_url_fetch import fetch_job_posting_page
from app.services.job_url_security import assert_url_is_safe_to_fetch
from app.services.skill_normalization import NormalizedSkillMatch

# Below this, extraction is treated as having failed rather than handed back
# as a near-empty preview — matches JobProfileCreate.description's own
# min_length=20 floor with headroom for a genuinely thin-but-real posting.
MIN_DESCRIPTION_LENGTH = 60


@dataclass(frozen=True)
class JobUrlImportPreview:
    source_url: str
    extraction_method: str
    title: str | None
    company: str | None
    location: str | None
    employment_type: str | None
    compensation: str | None
    posted_date: str | None
    description: str
    experience_required: str | None
    experience_evidence: str | None
    required_skills: list[JobRequirementSkillOut]
    preferred_skills: list[JobRequirementSkillOut]
    warnings: list[str]


class JobUrlImportService:
    def __init__(self, db: Session):
        self.db = db
        self.skills = SkillRepository(db)

    def preview(self, raw_url: str) -> JobUrlImportPreview:
        url = assert_url_is_safe_to_fetch(raw_url)
        page = fetch_job_posting_page(url)
        extracted = extract_job_posting(page.html)

        description = extracted.description.strip()
        if len(description) < MIN_DESCRIPTION_LENGTH:
            raise JobUrlExtractionFailedError()

        catalog = self.skills.list_catalog()
        required_matches, preferred_matches = classify_required_and_preferred_skills(
            description, catalog
        )
        experience = extract_experience(description)

        return JobUrlImportPreview(
            source_url=page.url,
            extraction_method=extracted.extraction_method,
            title=extracted.title,
            company=extracted.company,
            location=extracted.location,
            employment_type=extracted.employment_type,
            compensation=extracted.compensation,
            posted_date=extracted.posted_date,
            description=description,
            experience_required=experience.required if experience else None,
            experience_evidence=experience.evidence if experience else None,
            required_skills=self._to_skill_outs(required_matches, catalog),
            preferred_skills=self._to_skill_outs(preferred_matches, catalog),
            warnings=self._warnings(extracted),
        )

    @staticmethod
    def _warnings(extracted: ExtractedJobPosting) -> list[str]:
        warnings: list[str] = []
        if extracted.extraction_method == "HTML_FALLBACK":
            warnings.append(
                "No structured job data (JSON-LD) was found on this page — the title and "
                "description were extracted from the raw page text, so double-check them "
                "before saving."
            )
        if not extracted.title:
            warnings.append("Could not detect a job title — enter one before saving.")
        if not extracted.company:
            warnings.append("Could not detect a company name.")
        if not extracted.location:
            warnings.append("Could not detect a location.")
        return warnings

    @staticmethod
    def _to_skill_outs(
        matches: list[NormalizedSkillMatch], catalog: list[Skill]
    ) -> list[JobRequirementSkillOut]:
        by_id = {skill.id: skill for skill in catalog}
        outs: list[JobRequirementSkillOut] = []
        for match in matches:
            skill = by_id.get(match.skill_id)
            if skill is None:
                continue
            outs.append(
                JobRequirementSkillOut(
                    skill_id=match.skill_id,
                    name=skill.name,
                    category=skill.category,
                    matched_text=match.matched_text,
                    match_type=match.match_type,
                )
            )
        return outs
