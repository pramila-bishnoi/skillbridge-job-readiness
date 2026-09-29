"""Application persistence."""

from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.application import Application
from app.models.enums import ApplicationStatus
from app.models.job import Job
from app.schemas.application import ApplicationSort

SCORE_BUCKETS: tuple[tuple[str, float, float], ...] = (
    ("0–24", 0.0, 25.0),
    ("25–49", 25.0, 50.0),
    ("50–74", 50.0, 75.0),
    ("75–100", 75.0, 101.0),
)


class ApplicationRepository:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------- reads ----
    def get_by_id(self, application_id: int) -> Application | None:
        stmt = (
            select(Application)
            .options(joinedload(Application.job))
            .where(Application.id == application_id)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_code_and_email(self, application_code: str, email: str) -> Application | None:
        """Tracking lookup. BOTH the code and the email must match — the code
        alone is not enough, so a leaked code does not expose a candidate."""
        stmt = (
            select(Application)
            .options(joinedload(Application.job))
            .where(
                Application.application_code == application_code.strip().upper(),
                func.lower(Application.email) == email.strip().lower(),
            )
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def code_exists(self, application_code: str) -> bool:
        stmt = select(func.count(Application.id)).where(
            Application.application_code == application_code
        )
        return self.db.execute(stmt).scalar_one() > 0

    def find_live_application(self, job_id: int, email: str) -> Application | None:
        """A non-rejected application by this email for this job, if any.

        Backs the duplicate-application business rule. The database enforces the
        same thing with a partial unique index, as a backstop against races.
        """
        stmt = select(Application).where(
            Application.job_id == job_id,
            func.lower(Application.email) == email.strip().lower(),
            Application.status != ApplicationStatus.REJECTED,
        )
        return self.db.execute(stmt).scalars().first()

    def list_for_job(self, job_id: int) -> list[Application]:
        stmt = (
            select(Application)
            .options(joinedload(Application.job))
            .where(Application.job_id == job_id)
            .order_by(Application.id.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def _apply_filters(
        self,
        stmt: Select,
        *,
        search: str | None,
        job_id: int | None,
        status: ApplicationStatus | None,
        date_from: date | None,
        date_to: date | None,
        department: str | None,
        has_resume: bool | None,
        min_score: float | None,
        max_score: float | None,
    ) -> Select:
        if department:
            stmt = stmt.join(Job, Job.id == Application.job_id)
            stmt = stmt.where(Job.department == department)
        if search:
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    Application.name.ilike(pattern),
                    Application.email.ilike(pattern),
                    Application.application_code.ilike(pattern),
                    Application.experience.ilike(pattern),
                    Application.phone.ilike(pattern),
                    Application.cover_note.ilike(pattern),
                    Application.resume_text.ilike(pattern),
                )
            )
        if job_id:
            stmt = stmt.where(Application.job_id == job_id)
        if status:
            stmt = stmt.where(Application.status == status)
        if date_from:
            stmt = stmt.where(Application.created_at >= datetime.combine(date_from, time.min))
        if date_to:
            stmt = stmt.where(Application.created_at <= datetime.combine(date_to, time.max))
        if has_resume is True:
            stmt = stmt.where(Application.resume_key.isnot(None))
        elif has_resume is False:
            stmt = stmt.where(Application.resume_key.is_(None))
        if min_score is not None:
            stmt = stmt.where(Application.match_score >= min_score)
        if max_score is not None:
            stmt = stmt.where(Application.match_score <= max_score)
        return stmt

    @staticmethod
    def _apply_sort(stmt: Select, sort: ApplicationSort) -> Select:
        ordering = {
            ApplicationSort.NEWEST: (Application.created_at.desc(), Application.id.desc()),
            ApplicationSort.OLDEST: (Application.created_at.asc(), Application.id.asc()),
            ApplicationSort.MATCH_DESC: (
                Application.match_score.desc().nulls_last(),
                Application.id.desc(),
            ),
            ApplicationSort.MATCH_ASC: (
                Application.match_score.asc().nulls_last(),
                Application.id.asc(),
            ),
            ApplicationSort.NAME_ASC: (Application.name.asc(), Application.id.asc()),
        }[sort]
        return stmt.order_by(*ordering)

    def list_applications(
        self,
        *,
        search: str | None = None,
        job_id: int | None = None,
        status: ApplicationStatus | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        department: str | None = None,
        has_resume: bool | None = None,
        min_score: float | None = None,
        max_score: float | None = None,
        sort: ApplicationSort = ApplicationSort.NEWEST,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Application], int]:
        filters = {
            "search": search,
            "job_id": job_id,
            "status": status,
            "date_from": date_from,
            "date_to": date_to,
            "department": department,
            "has_resume": has_resume,
            "min_score": min_score,
            "max_score": max_score,
        }

        total = self.db.execute(
            self._apply_filters(select(func.count(Application.id)), **filters)
        ).scalar_one()

        stmt = self._apply_filters(select(Application), **filters)
        stmt = (
            self._apply_sort(stmt, sort)
            .options(joinedload(Application.job))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self.db.execute(stmt).scalars().all()), total

    # ------------------------------------------------- dashboard aggregates --
    def count(self, *, status: ApplicationStatus | None = None) -> int:
        stmt = select(func.count(Application.id))
        if status:
            stmt = stmt.where(Application.status == status)
        return self.db.execute(stmt).scalar_one()

    def count_by_status(self) -> dict[ApplicationStatus, int]:
        stmt = select(Application.status, func.count(Application.id)).group_by(Application.status)
        return dict(self.db.execute(stmt).all())

    def count_by_department(self) -> list[tuple[str, int]]:
        stmt = (
            select(Job.department, func.count(Application.id))
            .join(Job, Job.id == Application.job_id)
            .group_by(Job.department)
            .order_by(func.count(Application.id).desc())
        )
        return list(self.db.execute(stmt).all())

    def count_by_location(self) -> list[tuple[str, int]]:
        stmt = (
            select(Job.location, func.count(Application.id))
            .join(Job, Job.id == Application.job_id)
            .group_by(Job.location)
            .order_by(func.count(Application.id).desc())
        )
        return list(self.db.execute(stmt).all())

    def count_with_resume(self) -> int:
        stmt = select(func.count(Application.id)).where(Application.resume_key.isnot(None))
        return self.db.execute(stmt).scalar_one()

    def count_scored(self) -> int:
        stmt = select(func.count(Application.id)).where(Application.match_score.isnot(None))
        return self.db.execute(stmt).scalar_one()

    def average_match_score(self) -> float | None:
        stmt = select(func.avg(Application.match_score)).where(Application.match_score.isnot(None))
        value = self.db.execute(stmt).scalar_one()
        return round(float(value), 1) if value is not None else None

    def match_score_buckets(self) -> list[tuple[str, int]]:
        """Four bands plus an 'Unscored' bucket for applications with no cosine yet."""
        unscored = self.db.execute(
            select(func.count(Application.id)).where(Application.match_score.is_(None))
        ).scalar_one()
        rows: list[tuple[str, int]] = []
        for label, low, high in SCORE_BUCKETS:
            count = self.db.execute(
                select(func.count(Application.id)).where(
                    Application.match_score >= low,
                    Application.match_score < high,
                )
            ).scalar_one()
            rows.append((label, count))
        rows.append(("Unscored", unscored))
        return rows

    def counts_by_day(self, since: datetime) -> dict[date, int]:
        day_expr = func.date(Application.created_at)
        stmt = (
            select(day_expr, func.count(Application.id))
            .where(Application.created_at >= since)
            .group_by(day_expr)
        )
        result: dict[date, int] = {}
        for raw_day, count in self.db.execute(stmt).all():
            if raw_day is None:
                continue
            if isinstance(raw_day, datetime):
                result[raw_day.date()] = count
            elif isinstance(raw_day, date):
                result[raw_day] = count
            else:
                result[date.fromisoformat(str(raw_day))] = count
        return result

    def top_by_match(self, limit: int = 5) -> list[Application]:
        stmt = (
            select(Application)
            .options(joinedload(Application.job))
            .where(Application.match_score.isnot(None))
            .order_by(Application.match_score.desc(), Application.id.asc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def recent(self, limit: int = 5) -> list[Application]:
        stmt = (
            select(Application)
            .options(joinedload(Application.job))
            .order_by(Application.created_at.desc(), Application.id.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    # ------------------------------------------------------------ writes ----
    def add(self, application: Application) -> Application:
        self.db.add(application)
        self.db.flush()
        return application
