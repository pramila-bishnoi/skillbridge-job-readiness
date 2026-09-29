"""Student profile and resume endpoints for SkillBridge Phase 1."""

from __future__ import annotations

from fastapi import APIRouter, File, UploadFile, status

from app.api.deps import CurrentStudent, DbSession
from app.core.config import settings
from app.core.exceptions import ResumeTooLargeError, ValidationError
from app.schemas.skill import StudentSkillOut
from app.schemas.student_profile import (
    StudentProfileCreate,
    StudentProfileCreatedResponse,
    StudentProfileResponse,
    StudentProfileUpdate,
)
from app.services.student_profiles import StudentProfileService

router = APIRouter(prefix="/student", tags=["student profile"])
_CHUNK = 64 * 1024


async def _read_upload(upload: UploadFile) -> bytes:
    buffer = bytearray()
    while chunk := await upload.read(_CHUNK):
        buffer.extend(chunk)
        if len(buffer) > settings.resume_max_bytes:
            raise ResumeTooLargeError(
                f"Resume exceeds the maximum allowed size of {settings.resume_max_bytes / (1024 * 1024):.0f} MB."
            )
    return bytes(buffer)


@router.post("/profiles", response_model=StudentProfileCreatedResponse, status_code=status.HTTP_201_CREATED)
def create_profile(payload: StudentProfileCreate, db: DbSession) -> StudentProfileCreatedResponse:
    return StudentProfileService(db).create(payload)


@router.get("/profile", response_model=StudentProfileResponse)
def get_profile(profile: CurrentStudent, db: DbSession) -> StudentProfileResponse:
    return StudentProfileService(db).get(profile)


@router.patch("/profile", response_model=StudentProfileResponse)
def update_profile(
    payload: StudentProfileUpdate, profile: CurrentStudent, db: DbSession
) -> StudentProfileResponse:
    return StudentProfileService(db).update(profile, payload)


@router.get("/profile/skills", response_model=list[StudentSkillOut])
def get_profile_skills(profile: CurrentStudent, db: DbSession) -> list[StudentSkillOut]:
    """The student's normalized skills on their own, for a caller that only
    needs the skill list (e.g. a future job-matching feature) without the
    rest of the profile."""
    return StudentProfileService(db).list_skills(profile)


@router.post("/profile/resume", response_model=StudentProfileResponse)
async def upload_resume(
    profile: CurrentStudent, db: DbSession, resume: UploadFile = File(...)
) -> StudentProfileResponse:
    if not resume.filename:
        raise ValidationError("Please choose a resume file.")
    data = await _read_upload(resume)
    return StudentProfileService(db).upload_resume(profile, resume.filename, resume.content_type, data)