from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.deps import require_role
from app.models import ExamSession, Quiz, Question, Option, User
from app.schemas.quiz import (
    QuizCreate, QuizRead, QuizSummary, QuestionRead, QuestionUpdate,
)
from app.services.quiz_service import run_generation

router = APIRouter(prefix="/quizzes", tags=["quizzes"])
questions_router = APIRouter(prefix="/questions", tags=["questions"])

teacher_only = require_role("teacher", "admin")


def get_owned_quiz(db: Session, quiz_id: int, user: User) -> Quiz:
    quiz = db.scalar(
        select(Quiz)
        .where(Quiz.id == quiz_id)
        .options(selectinload(Quiz.questions).selectinload(Question.options))
    )
    if not quiz or (user.role != "admin" and quiz.teacher_id != user.id):
        raise HTTPException(status_code=404, detail="QCM introuvable")
    return quiz


@router.post("", response_model=QuizRead, status_code=201)
def create_quiz(
    data: QuizCreate,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(teacher_only),
):
    quiz = Quiz(
        teacher_id=user.id,
        specialty=data.specialty.strip(),
        subject=data.subject.strip(),
        level=data.level.strip(),
        nb_questions=data.nb_questions,
        chapters=data.chapters,
        status="GENERATING",
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    background.add_task(run_generation, quiz.id)
    return quiz


@router.get("", response_model=list[QuizSummary])
def list_quizzes(db: Session = Depends(get_db), user: User = Depends(teacher_only)):
    query = select(Quiz).order_by(Quiz.id.desc())
    if user.role != "admin":
        query = query.where(Quiz.teacher_id == user.id)
    return db.scalars(query).all()


@router.get("/{quiz_id}", response_model=QuizRead)
def get_quiz(quiz_id: int, db: Session = Depends(get_db), user: User = Depends(teacher_only)):
    return get_owned_quiz(db, quiz_id, user)


@router.post("/{quiz_id}/retry", response_model=QuizRead)
def retry_generation(
    quiz_id: int,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(teacher_only),
):
    quiz = get_owned_quiz(db, quiz_id, user)
    if quiz.status not in ("FAILED", "DRAFT"):
        raise HTTPException(status_code=409, detail="Génération impossible dans cet état")
    quiz.status = "GENERATING"
    quiz.error = None
    db.commit()
    background.add_task(run_generation, quiz.id)
    return get_owned_quiz(db, quiz_id, user)


@router.post("/{quiz_id}/validate", response_model=QuizRead)
def validate_quiz(quiz_id: int, db: Session = Depends(get_db), user: User = Depends(teacher_only)):
    quiz = get_owned_quiz(db, quiz_id, user)
    if quiz.status not in ("DRAFT", "VALIDATED"):
        raise HTTPException(status_code=409, detail="Le QCM n'est pas prêt à être validé")

    usable = [q for q in quiz.questions if q.status != "REJECTED"]
    if len(usable) < quiz.nb_questions:
        raise HTTPException(
            status_code=422,
            detail=f"Il faut au moins {quiz.nb_questions} questions retenues, vous en avez {len(usable)}",
        )
    for q in usable:
        if not any(o.is_correct for o in q.options):
            raise HTTPException(status_code=422, detail=f"La question {q.id} n'a aucune bonne réponse")
        q.status = "VALIDATED"
    quiz.status = "VALIDATED"
    db.commit()
    return get_owned_quiz(db, quiz_id, user)


@router.delete("/{quiz_id}", status_code=204)
def delete_quiz(quiz_id: int, db: Session = Depends(get_db), user: User = Depends(teacher_only)):
    quiz = get_owned_quiz(db, quiz_id, user)
    if quiz.status == "GENERATING":
        raise HTTPException(status_code=409, detail="Génération en cours : réessayez une fois terminée")
    nb_sessions = db.query(ExamSession).filter(ExamSession.quiz_id == quiz.id).count()
    if nb_sessions:
        raise HTTPException(
            status_code=409,
            detail=f"Cette banque est utilisée par {nb_sessions} session(s) d'examen : suppression impossible",
        )
    db.delete(quiz)  # questions et options supprimées en cascade
    db.commit()


def get_owned_question(db: Session, question_id: int, user: User) -> Question:
    question = db.scalar(
        select(Question).where(Question.id == question_id).options(selectinload(Question.options))
    )
    if not question:
        raise HTTPException(status_code=404, detail="Question introuvable")
    get_owned_quiz(db, question.quiz_id, user)  # vérifie les droits
    return question


@questions_router.patch("/{question_id}", response_model=QuestionRead)
def update_question(
    question_id: int,
    data: QuestionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(teacher_only),
):
    question = get_owned_question(db, question_id, user)
    if question.quiz.status == "VALIDATED":
        raise HTTPException(status_code=409, detail="QCM déjà validé : modification impossible")

    changes = data.model_dump(exclude_unset=True)
    options = changes.pop("options", None)
    for field, value in changes.items():
        setattr(question, field, value)
    if options is not None:
        question.options = [Option(text=o["text"], is_correct=o["is_correct"]) for o in options]
    db.commit()
    db.refresh(question)
    return question


@questions_router.delete("/{question_id}", status_code=204)
def delete_question(
    question_id: int, db: Session = Depends(get_db), user: User = Depends(teacher_only)
):
    question = get_owned_question(db, question_id, user)
    if question.quiz.status == "VALIDATED":
        raise HTTPException(status_code=409, detail="QCM déjà validé : suppression impossible")
    db.delete(question)
    db.commit()