from datetime import datetime
from sqlalchemy import (
    String, Text, ForeignKey, DateTime, Float, JSON, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


class ExamSession(Base):
    __tablename__ = "exam_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id"))
    group_id: Mapped[int] = mapped_column(ForeignKey("student_groups.id"))
    opens_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    closes_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[int]
    questions_per_student: Mapped[int]
    points_per_question: Mapped[float] = mapped_column(Float, default=1.0)
    # ALL_OR_NOTHING | PARTIAL | PARTIAL_PENALTY
    scoring_rule: Mapped[str] = mapped_column(String(30), default="ALL_OR_NOTHING")
    penalty: Mapped[float] = mapped_column(Float, default=0.0)
    # DRAFT | OPEN | CLOSED
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")


class Attempt(Base):
    __tablename__ = "attempts"
    __table_args__ = (UniqueConstraint("session_id", "student_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("exam_sessions.id", ondelete="CASCADE")
    )
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    seed: Mapped[str] = mapped_column(String(100))
    # NOT_STARTED | IN_PROGRESS | SUBMITTED | GRADED
    status: Mapped[str] = mapped_column(String(20), default="NOT_STARTED")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    auto_score: Mapped[float | None] = mapped_column(Float)
    final_score: Mapped[float | None] = mapped_column(Float)
    teacher_comment: Mapped[str | None] = mapped_column(Text)


class AttemptQuestion(Base):
    __tablename__ = "attempt_questions"
    __table_args__ = (UniqueConstraint("attempt_id", "question_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    attempt_id: Mapped[int] = mapped_column(
        ForeignKey("attempts.id", ondelete="CASCADE")
    )
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    position: Mapped[int]
    option_order: Mapped[list] = mapped_column(JSON)  # liste d'ids d'options mélangés


class Answer(Base):
    __tablename__ = "answers"
    __table_args__ = (UniqueConstraint("attempt_id", "question_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    attempt_id: Mapped[int] = mapped_column(
        ForeignKey("attempts.id", ondelete="CASCADE")
    )
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    selected_option_ids: Mapped[list] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(100))
    details: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )