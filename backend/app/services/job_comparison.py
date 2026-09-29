"""Job-comparison orchestration (Phase 7).

Purely a read: every job passed in must already have a Phase 4
``MatchAnalysis`` — comparison never triggers one — and each job's
matched/missing skill sets come directly from that analysis's existing
``SkillGap`` rows. Nothing here reclassifies a skill, recomputes a
readiness score, or writes anything to the database.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import JobProfileNotFoundError, JobsNotAnalyzedError
from app.models.enums import SkillGapType
from app.models.student_profile import StudentProfile
from app.repositories.job_profiles import JobProfileRepository
from app.repositories.match_analyses import MatchAnalysisRepository
from app.repositories.skill_gaps import SkillGapRepository
from app.schemas.job_comparison import JobComparisonEntry, JobComparisonResult
from app.services.job_comparison_rules import JobSkillSets, compare


class JobComparisonService:
    def __init__(self, db: Session):
        self.db = db
        self.job_profiles = JobProfileRepository(db)
        self.match_analyses = MatchAnalysisRepository(db)
        self.skill_gaps = SkillGapRepository(db)

    def compare(self, profile: StudentProfile, job_profile_ids: list[int]) -> JobComparisonResult:
        job_profiles = {}
        for job_profile_id in job_profile_ids:
            job_profile = self.job_profiles.get_by_id(job_profile_id)
            # Same "not found, not forbidden" posture as every other saved-job
            # route: a job owned by a different student must not be
            # distinguishable from one that does not exist.
            if job_profile is None or job_profile.student_profile_id != profile.id:
                raise JobProfileNotFoundError()
            job_profiles[job_profile_id] = job_profile

        analyses = {
            analysis.job_profile_id: analysis
            for analysis in self.match_analyses.list_for_jobs(profile.id, job_profile_ids)
        }
        not_analyzed = [
            job_profile_id for job_profile_id in job_profile_ids if job_profile_id not in analyses
        ]
        if not_analyzed:
            raise JobsNotAnalyzedError(details={"job_profile_ids": not_analyzed})

        job_sets: list[JobSkillSets] = []
        skills_by_job: dict[int, tuple[frozenset[str], frozenset[str]]] = {}
        for job_profile_id in job_profile_ids:
            gap_rows = self.skill_gaps.list_for_analysis(analyses[job_profile_id].id)
            matched = frozenset(
                gap.skill.name for gap in gap_rows if gap.gap_type == SkillGapType.MATCHED
            )
            missing = frozenset(
                gap.skill.name for gap in gap_rows if gap.gap_type != SkillGapType.MATCHED
            )
            job_sets.append(JobSkillSets(job_profile_id=job_profile_id, matched=matched, missing=missing))
            skills_by_job[job_profile_id] = (matched, missing)

        sets = compare(job_sets)

        entries = []
        for job_profile_id in job_profile_ids:
            job_profile = job_profiles[job_profile_id]
            analysis = analyses[job_profile_id]
            matched, missing = skills_by_job[job_profile_id]
            entries.append(
                JobComparisonEntry(
                    job_profile_id=job_profile_id,
                    title=job_profile.title,
                    company=job_profile.company,
                    readiness_score=analysis.readiness_score,
                    required_skill_coverage=analysis.required_skill_coverage,
                    preferred_skill_coverage=analysis.preferred_skill_coverage,
                    matched_skills=sorted(matched),
                    missing_skills=sorted(missing),
                    unique_missing_skills=sorted(sets.unique_missing_skills[job_profile_id]),
                )
            )

        return JobComparisonResult(
            jobs=entries,
            common_skills=sorted(sets.common_skills),
            common_missing_skills=sorted(sets.common_missing_skills),
        )
