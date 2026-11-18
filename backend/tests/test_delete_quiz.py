from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models.exam import ExamSession
from app.models.quiz import Option, Question, Quiz
from app.models.user import Group, User
from app.routers.quizzes import delete_quiz

engine = create_engine(
    "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def init_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def make_quiz(db, prof, status="DRAFT"):
    quiz = Quiz(teacher_id=prof.id, specialty="Info", subject="Algo", level="L1", nb_questions=1, status=status)
    q = Question(statement="Q ?", difficulty="facile", status="GENERATED")
    q.options = [Option(text="A", is_correct=True), Option(text="B", is_correct=False)]
    quiz.questions = [q]
    db.add(quiz)
    db.commit()
    return quiz


def make_prof(db, email="prof@test.fr"):
    prof = User(name="Prof", email=email, password_hash="h", role="teacher")
    db.add(prof)
    db.commit()
    return prof


def test_delete_quiz_removes_questions_and_options():
    with TestingSessionLocal() as db:
        prof = make_prof(db)
        quiz = make_quiz(db, prof)
        delete_quiz(quiz.id, db=db, user=prof)
        assert db.query(Quiz).count() == 0
        assert db.query(Question).count() == 0
        assert db.query(Option).count() == 0


def test_delete_quiz_refused_when_used_by_session():
    with TestingSessionLocal() as db:
        prof = make_prof(db)
        quiz = make_quiz(db, prof, status="VALIDATED")
        group = Group(name="G", teacher_id=prof.id)
        db.add(group)
        db.commit()
        now = datetime.now(timezone.utc)
        db.add(ExamSession(
            quiz_id=quiz.id, group_id=group.id, opens_at=now, closes_at=now + timedelta(hours=1),
            duration_minutes=30, questions_per_student=1,
        ))
        db.commit()
        with pytest.raises(HTTPException) as exc:
            delete_quiz(quiz.id, db=db, user=prof)
        assert exc.value.status_code == 409
        assert db.query(Quiz).count() == 1


def test_delete_quiz_refused_while_generating():
    with TestingSessionLocal() as db:
        prof = make_prof(db)
        quiz = make_quiz(db, prof, status="GENERATING")
        with pytest.raises(HTTPException) as exc:
            delete_quiz(quiz.id, db=db, user=prof)
        assert exc.value.status_code == 409


def test_delete_quiz_of_other_teacher_not_found():
    with TestingSessionLocal() as db:
        prof = make_prof(db)
        other = make_prof(db, "autre@test.fr")
        quiz = make_quiz(db, prof)
        with pytest.raises(HTTPException) as exc:
            delete_quiz(quiz.id, db=db, user=other)
        assert exc.value.status_code == 404
