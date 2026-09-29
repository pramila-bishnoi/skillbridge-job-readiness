"""Shared FastAPI dependencies.

``get_current_admin`` is the single gate in front of every administrative
endpoint. There is no other way into the admin API — no query-string flag, no
"internal" header (RESTRICTIONS.md #25).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import UnauthorizedError
from app.db.session import get_db
from app.models.admin import Admin
from app.models.student_profile import StudentProfile
from app.services.auth import AuthService

DbSession = Annotated[Session, Depends(get_db)]

# auto_error=False so a missing header raises our enveloped UnauthorizedError
# instead of Starlette's bare {"detail": "Not authenticated"}.
bearer_scheme = HTTPBearer(auto_error=False, description="Admin JWT access token")


def get_current_admin(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
) -> Admin:
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError("An administrator access token is required.")
    return AuthService(db).resolve_admin_from_token(credentials.credentials)


CurrentAdmin = Annotated[Admin, Depends(get_current_admin)]

student_bearer_scheme = HTTPBearer(auto_error=False, description="Student profile access token")


def get_current_student(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(student_bearer_scheme)] = None,
) -> StudentProfile:
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError("A student profile token is required.")
    from app.core.security import verify_student_access_token

    profile = db.get(StudentProfile, verify_student_access_token(credentials.credentials))
    if profile is None:
        raise UnauthorizedError("The student profile is no longer available.")
    return profile


CurrentStudent = Annotated[StudentProfile, Depends(get_current_student)]
