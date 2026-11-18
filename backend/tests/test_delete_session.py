from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models.exam import Answer, Attempt, AttemptQuestion, AuditLog, ExamSession
from app.models.quiz import Option, Question, Quiz
from app.models.user import Group, User
from app.routers.quizzes import delete_quiz
from app.routers.sessions import delete_session, publish_session

engine = create_engine(
    "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def init_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def setup_published_session(db):
    prof = User(name="Prof", email="prof@test.fr", password_hash="h", role="teacher")
    student = User(name="Ada", email="ada@test.fr", password_hash="h", role="student")
    db.add_all([prof, student])
    db.commit()

    quiz = Quiz(teacher_id=prof.id, specialty="Info", subject="Algo", level="L1", nb_questions=1, status="VALIDATED")
    q = Question(statement="Q ?", difficulty="facile", status="VALIDATED")
    q.options = [Option(text="A", is_correct=True), Option(text="B", is_correct=False)]
    quiz.questions = [q]
    group = Group(name="G", teacher_id=prof.id)
    group.students = [student]
    db.add_all([quiz, group])
    db.commit()

    now = datetime.now(timezone.utc)
    sess = ExamSession(
        quiz_id=quiz.id, group_id=group.id, opens_at=now, closes_at=now + timedelta(hours=1),
        duration_minutes=30, questions_per_student=1,
    )
    db.add(sess)
    db.commit()
    publish_session(sess.id, db=db, user=prof)
    return prof, quiz, sess


def test_delete_session_without_started_copies():
    with TestingSessionLocal() as db:
        prof, quiz, sess = setup_published_session(db)
        delete_session(sess.id, db=db, user=prof)
        assert db.query(ExamSession).count() == 0
        assert db.query(Attempt).count() == 0
        assert db.query(AttemptQuestion).count() == 0
        assert db.query(AuditLog).filter(AuditLog.action == "DELETE_SESSION").count() == 1
        # La banque n'est plus utilisée : elle peut maintenant être supprimée
        delete_quiz(quiz.id, db=db, user=prof)
        assert db.query(Quiz).count() == 0


def test_delete_session_with_started_copies_requires_force():
    with TestingSessionLocal() as db:
        prof, _, sess = setup_published_session(db)
        attempt = db.query(Attempt).one()
        attempt.status = "SUBMITTED"
        question_id = db.query(AttemptQuestion).one().question_id
        db.add(Answer(attempt_id=attempt.id, question_id=question_id, selected_option_ids=[]))
        db.commit()

        with pytest.raises(HTTPException) as exc:
            delete_session(sess.id, db=db, user=prof)
        assert exc.value.status_code == 409
        assert db.query(ExamSession).count() == 1

        delete_session(sess.id, force=True, db=db, user=prof)
        assert db.query(ExamSession).count() == 0
        assert db.query(Attempt).count() == 0
        assert db.query(Answer).count() == 0


def test_delete_session_of_other_teacher_forbidden():
    with TestingSessionLocal() as db:
        _, _, sess = setup_published_session(db)
        other = User(name="Autre", email="autre@test.fr", password_hash="h", role="teacher")
        db.add(other)
        db.commit()
        with pytest.raises(HTTPException) as exc:
            delete_session(sess.id, force=True, db=db, user=other)
        assert exc.value.status_code == 403
        assert db.query(ExamSession).count() == 1
