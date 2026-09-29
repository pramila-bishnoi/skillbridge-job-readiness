"""``job_profiles`` — a job description a student pasted in and saved.

Deliberately independent of ``jobs`` (the ATS's own listings table, see
``models/job.py``): a student analyzes job descriptions from anywhere, not
only roles posted on this careers site, and this feature must not couple to
— or be coupled to by — the recruiter matching/ranking engine
(``services/matching.py``). See ``docs/SKILLBRIDGE_ARCHITECTURE.md`` §7.2.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.job_skill import JobSkill
    from app.models.student_profile import StudentProfile


class JobProfile(Base, TimestampMixin):
    __tablename__ = "job_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_profile_id: Mapped[int] = mapped_column(
        ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    company: Mapped[str | None] = mapped_column(String(150), nullable=True)
    # The raw pasted text, kept verbatim so a matched skill or experience
    # requirement can always be traced back to what the student actually
    # pasted — the same explainability rule as StudentSkill.matched_text.
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Deterministic extraction results (services/job_analysis.py). Both null
    # when no experience requirement could be found — the analyzer never
    # guesses one.
    experience_required: Mapped[str | None] = mapped_column(String(100), nullable=True)
    experience_evidence: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Populated only when this job profile was created via "Import from Job
    # URL" (services/job_url_import.py); null for a pasted description, same
    # as every field below. Kept as plain strings — never re-parsed into a
    # stricter type — so the student's original source is always traceable
    # even when the extraction was only a best-effort guess (see
    # services/job_url_extraction.py's HTML fallback, which leaves these
    # null rather than invent a value).
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    employment_type_text: Mapped[str | None] = mapped_column(String(100), nullable=True)
    compensation_text: Mapped[str | None] = mapped_column(String(200), nullable=True)
    posted_date_text: Mapped[str | None] = mapped_column(String(100), nullable=True)

    student_profile: Mapped[StudentProfile] = relationship(back_populates="job_profiles")
    skills: Mapped[list[JobSkill]] = relationship(
        back_populates="job_profile", cascade="all, delete-orphan", passive_deletes=True
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<JobProfile {self.title!r} student={self.student_profile_id}>"
