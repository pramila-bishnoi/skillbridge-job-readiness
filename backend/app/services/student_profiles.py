"""Student profile and resume intelligence foundation."""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import StudentProfileExistsError
from app.core.security import create_student_access_token
from app.models.student_profile import StudentProfile
from app.models.student_skill import StudentSkill
from app.repositories.skills import SkillRepository
from app.repositories.student_profiles import StudentProfileRepository
from app.repositories.student_skills import StudentSkillRepository
from app.schemas.skill import StudentSkillOut
from app.schemas.student_profile import (
    StudentProfileCreate,
    StudentProfileCreatedResponse,
    StudentProfileResponse,
    StudentProfileUpdate,
)
from app.services.resume_text import extract_resume_text
from app.services.skill_normalization import normalize_skills
from app.services.storage import resume_storage


class StudentProfileService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = StudentProfileRepository(db)
        self.skills = SkillRepository(db)
        self.student_skills = StudentSkillRepository(db)

    def create(self, payload: StudentProfileCreate) -> StudentProfileCreatedResponse:
        email = str(payload.email).strip().lower()
        if self.repo.get_by_email(email) is not None:
            raise StudentProfileExistsError()
        profile = StudentProfile(email=email, **payload.model_dump(exclude={"email"}))
        self.repo.add(profile)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise StudentProfileExistsError() from exc
        self.db.refresh(profile)
        return StudentProfileCreatedResponse(
            profile=self._to_response(profile),
            access_token=create_student_access_token(profile.id),
            expires_in_seconds=30 * 24 * 60 * 60,
        )

    def get(self, profile: StudentProfile) -> StudentProfileResponse:
        return self._to_response(profile)

    def update(self, profile: StudentProfile, payload: StudentProfileUpdate) -> StudentProfileResponse:
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(profile, field, value.strip() if isinstance(value, str) else value)
        self.db.commit()
        self.db.refresh(profile)
        return self._to_response(profile)

    def upload_resume(
        self,
        profile: StudentProfile,
        filename: str,
        content_type: str | None,
        data: bytes,
    ) -> StudentProfileResponse:
        stored = resume_storage.store(f"STUDENT-{profile.id}", filename, content_type, data)
        extracted_text = extract_resume_text(filename, data)
        profile.resume_key = stored.key
        profile.resume_filename = filename
        profile.resume_text = extracted_text or None
        profile.resume_uploaded = True

        # Normalize against the canonical skill catalog (Phase 2) instead of
        # the Phase 1 hardcoded skill list. One evidence row per skill,
        # replacing whatever a previous upload had found.
        catalog = self.skills.list_catalog()
        matches = normalize_skills(extracted_text or "", catalog)
        self.student_skills.replace_for_profile(profile.id, matches)

        self.db.commit()
        self.db.refresh(profile)
        return self._to_response(profile)

    def list_skills(self, profile: StudentProfile) -> list[StudentSkillOut]:
        return [self._to_skill_out(row) for row in self.student_skills.list_for_profile(profile.id)]

    def _to_response(self, profile: StudentProfile) -> StudentProfileResponse:
        return StudentProfileResponse(
            id=profile.id,
            name=profile.name,
            email=profile.email,
            education=profile.education,
            skills=profile.skills,
            projects=profile.projects,
            experience=profile.experience,
            resume_uploaded=profile.resume_uploaded,
            resume_filename=profile.resume_filename,
            extracted_skills=self.list_skills(profile),
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )

    @staticmethod
    def _to_skill_out(row: StudentSkill) -> StudentSkillOut:
        return StudentSkillOut(
            skill_id=row.skill_id,
            name=row.skill.name,
            category=row.skill.category,
            matched_text=row.matched_text,
            match_type=row.match_type,
        )
