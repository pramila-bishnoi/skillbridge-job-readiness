"""Skill-progress endpoints for SkillBridge Phase 7.

Student-profile-scoped, not job-scoped — unlike readiness/preparation/
interview-prep, progress belongs to the student, not to any one saved job
(docs/SKILLBRIDGE_ARCHITECTURE.md §18: "Progress belongs to the student
profile, not to a single application").
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentStudent, DbSession
from app.schemas.skill_progress import SkillCatalogEntry, SkillProgressOut, SkillProgressUpdate
from app.services.skill_progress import SkillProgressService

router = APIRouter(prefix="/student/skill-progress", tags=["skill progress"])


@router.get("", response_model=list[SkillProgressOut])
def list_skill_progress(profile: CurrentStudent, db: DbSession) -> list[SkillProgressOut]:
    """Only skills the student has explicitly set a status for — sparse, not
    every catalog or resume skill."""
    return SkillProgressService(db).list_for_student(profile)


@router.get("/catalog", response_model=list[SkillCatalogEntry])
def list_skill_catalog(profile: CurrentStudent, db: DbSession) -> list[SkillCatalogEntry]:
    """The full canonical catalog, so the UI can offer a skill to track that
    isn't on the student's resume yet."""
    return SkillProgressService(db).list_catalog()


@router.patch("/{skill_id}", response_model=SkillProgressOut)
def update_skill_progress(
    skill_id: int, payload: SkillProgressUpdate, profile: CurrentStudent, db: DbSession
) -> SkillProgressOut:
    return SkillProgressService(db).update(profile, skill_id, payload.status)
