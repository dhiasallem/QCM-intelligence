from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base


class Quiz(Base):
    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    specialty: Mapped[str] = mapped_column(String(150))
    subject: Mapped[str] = mapped_column(String(150))
    level: Mapped[str] = mapped_column(String(80))
    nb_questions: Mapped[int]
    chapters: Mapped[str | None] = mapped_column(Text)
    provider: Mapped[str | None] = mapped_column(String(30))
    # GENERATING | DRAFT | VALIDATED | FAILED
    status: Mapped[str] = mapped_column(String(20), default="GENERATING")
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    questions: Mapped[list["Question"]] = relationship(
        back_populates="quiz", cascade="all, delete-orphan"
    )


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id", ondelete="CASCADE"))
    statement: Mapped[str] = mapped_column(Text)
    difficulty: Mapped[str] = mapped_column(String(20))  # facile | moyen | difficile
    chapter: Mapped[str | None] = mapped_column(String(150))
    explanation: Mapped[str | None] = mapped_column(Text)
    # GENERATED | VALIDATED | REJECTED
    status: Mapped[str] = mapped_column(String(20), default="GENERATED")

    quiz: Mapped[Quiz] = relationship(back_populates="questions")
    options: Mapped[list["Option"]] = relationship(
        back_populates="question", cascade="all, delete-orphan"
    )


class Option(Base):
    __tablename__ = "options"

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE")
    )
    text: Mapped[str] = mapped_column(Text)
    is_correct: Mapped[bool] = mapped_column(default=False)

    question: Mapped[Question] = relationship(back_populates="options")


class AiLog(Base):
    __tablename__ = "ai_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    quiz_id: Mapped[int | None] = mapped_column(ForeignKey("quizzes.id", ondelete="SET NULL"))
    provider: Mapped[str] = mapped_column(String(30))
    success: Mapped[bool]
    duration_ms: Mapped[int | None]
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )