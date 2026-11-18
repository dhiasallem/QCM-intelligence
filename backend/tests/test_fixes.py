"""Générations interrompues, suppression de groupe, clôture automatique des sessions."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models.exam import Attempt, ExamSession
from app.models.quiz import Option, Question, Quiz
from app.models.user import Group, User
from app.routers.attempts import get_or_start_attempt
from app.routers.groups import delete_group
from app.routers.sessions import get_session, list_sessions, publish_session
from app.services.quiz_service import recover_interrupted_generations

engine = create_engine(
    "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def init_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def setup(db, closes_in=timedelta(hours=1)):
    prof = User(name="Prof", email="prof@t.fr", password_hash="h", role="teacher")
    student = User(name="Ada", email="ada@t.fr", password_hash="h", role="student")
    db.add_all([prof, student])
    db.commit()
    quiz = Quiz(teacher_id=prof.id, specialty="Info", subject="Algo", level="L1", nb_questions=1, status="VALIDATED")
    q = Question(statement="Q ?", difficulty="facile", status="VALIDATED")
    q.options = [Option(text="A", is_correct=True), Option(text="B", is_correct=False)]
    quiz.questions = [q]
    group = Group(name="Groupe", teacher_id=prof.id)
    group.students = [student]
    db.add_all([quiz, group])
    db.commit()
    now = datetime.now(timezone.utc)
    sess = ExamSession(
        quiz_id=quiz.id, group_id=group.id, opens_at=now - timedelta(hours=2),
        closes_at=now + closes_in, duration_minutes=30, questions_per_student=1,
    )
    db.add(sess)
    db.commit()
    publish_session(sess.id, db=db, user=prof)
    return prof, student, group, sess


def test_interrupted_generation_becomes_failed():
    with TestingSessionLocal() as db:
        prof = User(name="Prof", email="prof@t.fr", password_hash="h", role="teacher")
        db.add(prof)
        db.commit()
        db.add_all([
            Quiz(teacher_id=prof.id, specialty="I", subject="Bloqué", level="L1", nb_questions=1, status="GENERATING"),
            Quiz(teacher_id=prof.id, specialty="I", subject="Prêt", level="L1", nb_questions=1, status="DRAFT"),
        ])
        db.commit()
        assert recover_interrupted_generations(db) == 1
        statuses = {q.subject: (q.status, q.error) for q in db.query(Quiz)}
        assert statuses["Bloqué"][0] == "FAILED" and "interrompue" in statuses["Bloqué"][1]
        assert statuses["Prêt"] == ("DRAFT", None)


def test_delete_group_with_sessions_is_refused():
    with TestingSessionLocal() as db:
        prof, _, group, _ = setup(db)
        with pytest.raises(HTTPException) as exc:
            delete_group(group.id, db=db, user=prof)
        assert exc.value.status_code == 409
        assert db.query(Group).count() == 1


def test_delete_empty_group():
    with TestingSessionLocal() as db:
        prof = User(name="Prof", email="prof@t.fr", password_hash="h", role="teacher")
        db.add(prof)
        db.commit()
        group = Group(name="Vide", teacher_id=prof.id)
        db.add(group)
        db.commit()
        delete_group(group.id, db=db, user=prof)
        assert db.query(Group).count() == 0


def test_expired_session_is_closed_and_in_progress_copy_is_scored():
    with TestingSessionLocal() as db:
        prof, student, _, sess = setup(db)
        attempt_id = db.query(Attempt).one().id
        get_or_start_attempt(attempt_id, db=db, current_user=student)  # l'étudiant commence

        # L'heure de clôture passe alors que la copie est encore en cours
        sess.closes_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()

        assert list_sessions(db=db, user=prof)[0].status == "CLOSED"
        attempt = db.get(Attempt, attempt_id)
        assert attempt.status == "SUBMITTED" and attempt.auto_score is not None


def test_open_session_stays_open():
    with TestingSessionLocal() as db:
        prof, _, _, sess = setup(db)
        assert get_session(sess.id, db=db, user=prof).status == "OPEN"


def test_not_started_copy_refused_after_close():
    with TestingSessionLocal() as db:
        prof, student, _, sess = setup(db, closes_in=timedelta(minutes=-1))
        list_sessions(db=db, user=prof)  # clôture la session
        with pytest.raises(HTTPException) as exc:
            get_or_start_attempt(db.query(Attempt).one().id, db=db, current_user=student)
        assert "terminé" in exc.value.detail
