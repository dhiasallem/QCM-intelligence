"""Inscription libre + groupes avec code d'accÃ¨s (fonctionnement faÃ§on Google Classroom)."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.migrations import ensure_group_codes
from app.models.exam import Attempt, ExamSession
from app.models.quiz import Option, Question, Quiz
from app.models.user import Group, User
from app.routers.attempts import list_my_attempts
from app.routers.auth import register
from app.routers.groups import (
    create_group, join_group, leave_group, list_my_groups, regenerate_group_code,
)
from app.routers.sessions import publish_session
from app.schemas.auth import RegisterRequest
from app.schemas.group import GroupCreate, JoinGroupRequest
from app.security import decode_access_token

engine = create_engine(
    "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def init_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def make_user(db, email, role):
    u = User(name=email.split("@")[0].title(), email=email, password_hash="h", role=role)
    db.add(u)
    db.commit()
    return u


def make_open_session(db, prof, group, closes_in=timedelta(hours=1)):
    quiz = Quiz(teacher_id=prof.id, specialty="Info", subject="Algo", level="L1", nb_questions=2, status="VALIDATED")
    for i in range(3):
        q = Question(statement=f"Q{i}", difficulty="facile", status="VALIDATED")
        q.options = [Option(text="A", is_correct=True), Option(text="B", is_correct=False)]
        quiz.questions.append(q)
    db.add(quiz)
    db.commit()
    now = datetime.now(timezone.utc)
    sess = ExamSession(
        quiz_id=quiz.id, group_id=group.id, opens_at=now - timedelta(minutes=5),
        closes_at=now + closes_in, duration_minutes=30, questions_per_student=2,
    )
    db.add(sess)
    db.commit()
    return sess


def test_register_teacher_and_student():
    with TestingSessionLocal() as db:
        token = register(RegisterRequest(name="Prof X", email="X@Univ.fr", password="password123", role="teacher"), db=db)
        payload = decode_access_token(token.access_token)
        user = db.query(User).one()
        assert user.email == "x@univ.fr" and user.role == "teacher"
        assert str(payload["sub"]) == str(user.id)

        with pytest.raises(HTTPException) as exc:
            register(RegisterRequest(name="Doublon", email="x@univ.fr", password="password123", role="student"), db=db)
        assert exc.value.status_code == 409


def test_register_admin_is_rejected():
    with pytest.raises(ValueError):
        RegisterRequest(name="Pirate", email="p@univ.fr", password="password123", role="admin")


def test_group_gets_unique_code_and_can_regenerate():
    with TestingSessionLocal() as db:
        prof = make_user(db, "prof@univ.fr", "teacher")
        g1 = create_group(GroupCreate(name="Groupe A"), db=db, user=prof)
        g2 = create_group(GroupCreate(name="Groupe B"), db=db, user=prof)
        assert len(g1.code) == 7 and g1.code != g2.code
        old = g1.code
        assert regenerate_group_code(g1.id, db=db, user=prof).code != old


def test_student_joins_with_code_and_receives_open_exam():
    with TestingSessionLocal() as db:
        prof = make_user(db, "prof@univ.fr", "teacher")
        early = make_user(db, "early@univ.fr", "student")
        late = make_user(db, "late@univ.fr", "student")
        group = create_group(GroupCreate(name="L1 Algo"), db=db, user=prof)

        # Le premier Ã©tudiant rejoint (code saisi en minuscules avec espaces)
        res = join_group(JoinGroupRequest(code=f" {group.code.lower()} "), db=db, user=early)
        assert res.group.name == "L1 Algo" and res.group.teacher_name == "Prof"
        assert res.new_exams == 0

        sess = make_open_session(db, prof, db.get(Group, group.id))
        publish_session(sess.id, db=db, user=prof)
        assert db.query(Attempt).count() == 1

        # Un Ã©tudiant qui rejoint aprÃ¨s la publication reÃ§oit quand mÃªme sa copie
        res = join_group(JoinGroupRequest(code=group.code), db=db, user=late)
        assert res.new_exams == 1
        exams = list_my_attempts(db=db, current_user=late)
        assert len(exams) == 1 and exams[0].group_name == "L1 Algo" and exams[0].can_start

        assert [g.name for g in list_my_groups(db=db, user=late)] == ["L1 Algo"]

        with pytest.raises(HTTPException) as exc:
            join_group(JoinGroupRequest(code=group.code), db=db, user=late)
        assert exc.value.status_code == 409


def test_join_does_not_give_closed_exam():
    with TestingSessionLocal() as db:
        prof = make_user(db, "prof@univ.fr", "teacher")
        first = make_user(db, "first@univ.fr", "student")
        late = make_user(db, "late@univ.fr", "student")
        group = create_group(GroupCreate(name="Groupe clos"), db=db, user=prof)
        join_group(JoinGroupRequest(code=group.code), db=db, user=first)
        sess = make_open_session(db, prof, db.get(Group, group.id), closes_in=timedelta(minutes=-1))
        publish_session(sess.id, db=db, user=prof)
        assert join_group(JoinGroupRequest(code=group.code), db=db, user=late).new_exams == 0


def test_student_leaves_group():
    with TestingSessionLocal() as db:
        prof = make_user(db, "prof@univ.fr", "teacher")
        ada = make_user(db, "ada@univ.fr", "student")
        group = create_group(GroupCreate(name="L1 Algo"), db=db, user=prof)
        join_group(JoinGroupRequest(code=group.code), db=db, user=ada)

        # Deux sessions : une copie rendue (à garder), une non commencée (à retirer)
        done = make_open_session(db, prof, db.get(Group, group.id))
        publish_session(done.id, db=db, user=prof)
        todo = make_open_session(db, prof, db.get(Group, group.id))
        publish_session(todo.id, db=db, user=prof)
        db.query(Attempt).filter(Attempt.session_id == done.id).one().status = "SUBMITTED"
        db.commit()

        leave_group(group.id, db=db, user=ada)

        assert list_my_groups(db=db, user=ada) == []
        remaining = db.query(Attempt).filter(Attempt.student_id == ada.id).all()
        assert [(a.session_id, a.status) for a in remaining] == [(done.id, "SUBMITTED")]

        # Il peut revenir avec le code, et récupère l'examen encore ouvert
        assert join_group(JoinGroupRequest(code=group.code), db=db, user=ada).new_exams == 1


def test_leave_group_not_member():
    with TestingSessionLocal() as db:
        prof = make_user(db, "prof@univ.fr", "teacher")
        ada = make_user(db, "ada@univ.fr", "student")
        group = create_group(GroupCreate(name="L1 Algo"), db=db, user=prof)
        with pytest.raises(HTTPException) as exc:
            leave_group(group.id, db=db, user=ada)
        assert exc.value.status_code == 404


def test_join_with_wrong_code():
    with TestingSessionLocal() as db:
        student = make_user(db, "s@univ.fr", "student")
        with pytest.raises(HTTPException) as exc:
            join_group(JoinGroupRequest(code="ZZZZZZZ"), db=db, user=student)
        assert exc.value.status_code == 404


def test_migration_adds_codes_to_existing_groups():
    legacy = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    with legacy.begin() as conn:
        conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, name VARCHAR, email VARCHAR, password_hash VARCHAR, role VARCHAR, is_active BOOLEAN, created_at DATETIME)"))
        conn.execute(text("CREATE TABLE student_groups (id INTEGER PRIMARY KEY, name VARCHAR(120), teacher_id INTEGER)"))
        conn.execute(text("INSERT INTO users (id, name, email, password_hash, role, is_active) VALUES (1, 'P', 'p@u.fr', 'h', 'teacher', 1)"))
        conn.execute(text("INSERT INTO student_groups (id, name, teacher_id) VALUES (1, 'A', 1), (2, 'B', 1)"))

    ensure_group_codes(legacy)
    ensure_group_codes(legacy)  # idempotent

    assert "code" in {c["name"] for c in inspect(legacy).get_columns("student_groups")}
    with legacy.connect() as conn:
        codes = [r[0] for r in conn.execute(text("SELECT code FROM student_groups"))]
    assert len(codes) == 2 and all(codes) and codes[0] != codes[1]
