"""``interview_questions`` — one generated question under an ``InterviewTopic``.

Phase 6. ``completed`` is a plain boolean, not the three-state
``PreparationItemStatus`` Phase 5 uses for preparation items — the task
specifies "completed/not-completed" for interview questions specifically,
and a binary flag is the honest representation of that, not a reused
richer enum that would imply a distinction (e.g. "in progress") this
feature does not make.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import InterviewDifficulty

if TYPE_CHECKING:
    from app.models.interview_topic import InterviewTopic


class InterviewQuestion(Base, TimestampMixin):
    __tablename__ = "interview_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    interview_topic_id: Mapped[int] = mapped_column(
        ForeignKey("interview_topics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question: Mapped[str] = mapped_column(String(500), nullable=False)
    difficulty: Mapped[InterviewDifficulty] = mapped_column(
        Enum(
            InterviewDifficulty,
            native_enum=False,
            length=10,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    topic: Mapped[InterviewTopic] = relationship(back_populates="questions")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<InterviewQuestion topic={self.interview_topic_id} completed={self.completed}>"
