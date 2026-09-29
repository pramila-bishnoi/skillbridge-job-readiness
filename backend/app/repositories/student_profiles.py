"""Student profile persistence."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.student_profile import StudentProfile


class StudentProfileRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, profile_id: int) -> StudentProfile | None:
        return self.db.execute(
            select(StudentProfile).where(StudentProfile.id == profile_id)
        ).scalar_one_or_none()

    def get_by_email(self, email: str) -> StudentProfile | None:
        return self.db.execute(
            select(StudentProfile).where(StudentProfile.email == email.strip().lower())
        ).scalar_one_or_none()

    def add(self, profile: StudentProfile) -> StudentProfile:
        self.db.add(profile)
        self.db.flush()
        return profile