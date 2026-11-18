import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models.user import User, Group
from app.models.quiz import Quiz, Question, Option
from app.models.exam import ExamSession, Attempt, AttemptQuestion, Answer
from app.schemas.group import GroupCreate, AddStudentsRequest
from app.schemas.session import SessionCreate
from app.schemas.attempt import SaveAnswersRequest, AttemptGradeUpdate
from app.routers.groups import create_group, add_students_to_group
from app.routers.quizzes import validate_quiz
from app.routers.sessions import (
    create_session,
    publish_session,
    list_session_attempts,
    export_session_results,
    cancel_question_in_session,
)
from app.routers.attempts import (
    list_my_attempts,
    get_or_start_attempt,
    save_answers,
    submit_attempt,
    get_attempt_review,
    grade_attempt,
)

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def init_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_complete_exam_lifecycle():
    with TestingSessionLocal() as db:
        # 1. Création des acteurs
        prof = User(name="Professeur Turing", email="turing@univ.fr", password_hash="hash", role="teacher")
        student = User(name="Ada Lovelace", email="ada@univ.fr", password_hash="hash", role="student")
        db.add_all([prof, student])
        db.commit()
        db.refresh(prof)
        db.refresh(student)

        # 2. Création du groupe et ajout de l'étudiant
        group = create_group(GroupCreate(name="Licence 1 Algo"), db=db, user=prof)
        assert group.id is not None

        group_updated = add_students_to_group(
            group.id,
            AddStudentsRequest(student_ids=[student.id]),
            db=db,
            user=prof,
        )
        assert len(group_updated.students) == 1

        # 3. Création d'une banque de questions pour le QCM
        quiz = Quiz(
            teacher_id=prof.id,
            specialty="Informatique",
            subject="Algorithmique",
            level="L1",
            nb_questions=3,
            status="DRAFT",
        )
        db.add(quiz)
        db.flush()

        for i in range(1, 7):
            diff = "facile" if i <= 2 else ("moyen" if i <= 4 else "difficile")
            q = Question(
                quiz_id=quiz.id,
                statement=f"Question secrète n°{i} sur les listes",
                difficulty=diff,
                chapter=f"Chapitre {(i % 2) + 1}",
                explanation=f"La réponse correcte est la 1ère car {i}",
                status="GENERATED",
            )
            q.options = [
                Option(text=f"Bonne réponse {i}", is_correct=True),
                Option(text=f"Mauvaise réponse A {i}", is_correct=False),
                Option(text=f"Mauvaise réponse B {i}", is_correct=False),
                Option(text=f"Mauvaise réponse C {i}", is_correct=False),
            ]
            db.add(q)
        db.commit()

        # Validation du Quiz par le professeur
        validated_quiz = validate_quiz(quiz.id, db=db, user=prof)
        assert validated_quiz.status == "VALIDATED"

        # 4. Création d'une session d'examen
        now = datetime.now(timezone.utc)
        sess_input = SessionCreate(
            quiz_id=quiz.id,
            group_id=group.id,
            opens_at=now - timedelta(minutes=5),
            closes_at=now + timedelta(hours=2),
            duration_minutes=30,
            questions_per_student=3,
            points_per_question=2.0,
            scoring_rule="ALL_OR_NOTHING",
            penalty=0.0,
        )
        sess_created = create_session(sess_input, db=db, user=prof)
        assert sess_created.status == "DRAFT"

        # 5. Publication de la session (génération des copies déterministes)
        sess_published = publish_session(sess_created.id, db=db, user=prof)
        assert sess_published.status == "OPEN"
        assert sess_published.total_attempts == 1

        # 6. Consultation de la liste des examens par l'étudiant
        my_exams = list_my_attempts(db=db, current_user=student)
        assert len(my_exams) == 1
        assert my_exams[0].status == "NOT_STARTED"
        assert my_exams[0].can_start is True
        attempt_id = my_exams[0].attempt_id

        # 7. Démarrage de l'examen par l'étudiant
        exam_take = get_or_start_attempt(attempt_id, db=db, current_user=student)
        assert exam_take.status == "IN_PROGRESS"
        assert len(exam_take.questions) == 3
        assert exam_take.remaining_seconds > 0

        # CONTRÔLE DE SÉCURITÉ MAJEUR : Pas de fuite de réponse ni explication
        for sq in exam_take.questions:
            assert sq.chapter is not None
            for opt in sq.options:
                assert not hasattr(opt, "is_correct")

        # 8. Sauvegarde automatique des réponses (autosave)
        # Choisissons la 1ère option de chaque question
        q1 = exam_take.questions[0]
        q2 = exam_take.questions[1]
        answers_payload = SaveAnswersRequest(
            answers={
                q1.id: [q1.options[0].id],
                q2.id: [q2.options[0].id],
            }
        )
        save_res = save_answers(attempt_id, answers_payload, db=db, current_user=student)
        assert save_res["status"] == "saved"

        # 9. Soumission de la copie
        submit_res = submit_attempt(attempt_id, db=db, current_user=student)
        assert submit_res.status == "SUBMITTED"

        # 10. Professeur consulte la liste des copies
        teacher_attempts = list_session_attempts(sess_created.id, db=db, user=prof)
        assert len(teacher_attempts) == 1
        assert teacher_attempts[0].status == "SUBMITTED"
        assert teacher_attempts[0].auto_score is not None

        # 11. Professeur consulte la revue détaillée de la copie
        review = get_attempt_review(attempt_id, db=db, current_user=prof)
        assert review.student_name == "Ada Lovelace"
        assert len(review.questions) == 3
        for rq in review.questions:
            assert rq.explanation is not None
            assert len(rq.options) == 4

        # 12. Professeur ajuste et valide la note finale
        grade_update = AttemptGradeUpdate(final_score=5.5, teacher_comment="Très bon raisonnement")
        graded = grade_attempt(attempt_id, grade_update, db=db, user=prof)
        assert graded.status == "GRADED"
        assert graded.final_score == 5.5
        assert graded.teacher_comment == "Très bon raisonnement"

        # 13. Export CSV des résultats
        csv_response = export_session_results(sess_created.id, db=db, user=prof)
        csv_body = csv_response.body.decode("utf-8")
        assert "Ada Lovelace" in csv_body
        assert "5.50" in csv_body
        assert "Très bon raisonnement" in csv_body

        # 14. Annulation d'une question défectueuse et recalcul automatique
        cancel_res = cancel_question_in_session(
            session_id=sess_created.id,
            question_id=q1.id,
            db=db,
            user=prof,
        )
        assert "annulée" in cancel_res["message"]
