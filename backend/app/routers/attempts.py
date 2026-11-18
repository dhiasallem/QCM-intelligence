from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload, joinedload

from app.db import get_db
from app.deps import get_current_user, require_role
from app.models.exam import ExamSession, Attempt, AttemptQuestion, Answer, AuditLog
from app.models.quiz import Question, Option
from app.models.user import User
from app.schemas.attempt import (
    StudentAttemptTake,
    StudentQuestion,
    StudentOption,
    SaveAnswersRequest,
    SubmitResponse,
    AttemptReview,
    ReviewQuestion,
    ReviewOption,
    AttemptGradeUpdate,
    StudentSessionSummary,
)
from app.services.scoring_service import compute_attempt_score, compute_question_score

router = APIRouter(prefix="/attempts", tags=["attempts"])
teacher_or_admin = require_role("teacher", "admin")


def get_current_utc() -> datetime:
    return datetime.now(timezone.utc)


def ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)



def submit_and_score_attempt(db: Session, attempt: Attempt, sess: ExamSession) -> None:
    """Calcule le score automatique et fige la tentative."""
    attempt.status = "SUBMITTED"
    attempt.submitted_at = get_current_utc()

    # Charger les questions de l'examen avec leurs options
    q_ids = [aq.question_id for aq in attempt.attempt_questions]
    questions = (
        db.scalars(
            select(Question)
            .where(Question.id.in_(q_ids))
            .options(selectinload(Question.options))
        )
        .all()
    )

    answers = db.scalars(
        select(Answer).where(Answer.attempt_id == attempt.id)
    ).all()
    ans_map = {ans.question_id: ans.selected_option_ids for ans in answers}

    score = compute_attempt_score(
        questions=questions,
        answers_map=ans_map,
        points_per_question=sess.points_per_question,
        scoring_rule=sess.scoring_rule,
        penalty=sess.penalty,
    )
    attempt.auto_score = score
    attempt.final_score = score


@router.get("/me", response_model=list[StudentSessionSummary])
def list_my_attempts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Liste tous les examens assignés à l'étudiant connecté."""
    attempts = db.scalars(
        select(Attempt)
        .where(Attempt.student_id == current_user.id)
        .options(
            joinedload(Attempt.session).joinedload(ExamSession.quiz),
            joinedload(Attempt.session).joinedload(ExamSession.group),
            selectinload(Attempt.attempt_questions),
        )
        .order_by(Attempt.id.desc())
    ).all()

    now = get_current_utc()
    results = []
    for a in attempts:
        sess = a.session
        sess_opens = ensure_utc(sess.opens_at)
        sess_closes = ensure_utc(sess.closes_at)
        can_start = (
            sess.status == "OPEN"
            and sess_opens <= now <= sess_closes
            and a.status in ("NOT_STARTED", "IN_PROGRESS")
        )
        max_score = len(a.attempt_questions) * sess.points_per_question
        results.append(
            StudentSessionSummary(
                session_id=sess.id,
                attempt_id=a.id,
                quiz_subject=sess.quiz.subject if sess.quiz else "Examen",
                group_name=sess.group.name if sess.group else None,
                opens_at=sess.opens_at,
                closes_at=sess.closes_at,
                duration_minutes=sess.duration_minutes,
                status=a.status,
                final_score=a.final_score if a.status == "GRADED" else None,
                auto_score=a.auto_score if a.status in ("SUBMITTED", "GRADED") else None,
                max_score=max_score,
                can_start=can_start,
            )
        )
    return results


@router.get("/{attempt_id}", response_model=StudentAttemptTake)
def get_or_start_attempt(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Charge la copie d'un étudiant ou démarre le chronomètre serveur si NOT_STARTED."""
    attempt = db.scalar(
        select(Attempt)
        .where(Attempt.id == attempt_id)
        .options(
            joinedload(Attempt.session).joinedload(ExamSession.quiz),
            selectinload(Attempt.attempt_questions).joinedload(AttemptQuestion.question).selectinload(Question.options),
            selectinload(Attempt.answers),
        )
    )
    if not attempt:
        raise HTTPException(status_code=404, detail="Tentative introuvable")

    # Vérification des droits
    if current_user.role == "student" and attempt.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Vous n'avez pas accès à cette copie")

    sess = attempt.session
    now = get_current_utc()
    sess_opens = ensure_utc(sess.opens_at)
    sess_closes = ensure_utc(sess.closes_at)

    # Une session CLOSED reste accessible ici : une copie démarrée est alors soumise
    # automatiquement (deadline dépassée), une copie non démarrée est refusée (clôture dépassée).
    if sess.status == "DRAFT":
        raise HTTPException(status_code=400, detail="Cette session n'est pas ouverte")

    if now < sess_opens:
        raise HTTPException(status_code=400, detail="L'examen n'a pas encore commencé")

    # Démarrage si non commencé
    if attempt.status == "NOT_STARTED":
        if now > sess_closes:
            raise HTTPException(status_code=400, detail="L'examen est terminé (date de clôture dépassée)")

        attempt.status = "IN_PROGRESS"
        attempt.started_at = now
        allowed_deadline = now + timedelta(minutes=sess.duration_minutes)
        attempt.deadline_at = min(allowed_deadline, sess_closes)
        db.commit()
        db.refresh(attempt)

    elif attempt.status == "IN_PROGRESS":
        # Vérifier si le temps imparti est écoulé -> soumission automatique
        attempt_deadline = ensure_utc(attempt.deadline_at)
        if attempt_deadline and now > attempt_deadline:
            submit_and_score_attempt(db, attempt, sess)
            db.commit()
            raise HTTPException(
                status_code=400,
                detail="Le temps imparti est écoulé. Votre copie a été automatiquement soumise.",
            )

    elif attempt.status in ("SUBMITTED", "GRADED"):
        raise HTTPException(
            status_code=400,
            detail="Cette copie a déjà été soumise.",
        )

    # Calcul des secondes restantes
    remaining = 0
    attempt_deadline = ensure_utc(attempt.deadline_at)
    if attempt_deadline:
        remaining = max(0, int((attempt_deadline - now).total_seconds()))

    # Construire la vue des questions dans l'ordre déterministe tiré pour cet étudiant
    # ATTENTION SECURITE : Ne jamais exposer is_correct ni explication !
    questions_out: list[StudentQuestion] = []
    
    # Ordonner les questions selon aq.position
    sorted_aqs = sorted(attempt.attempt_questions, key=lambda x: x.position)

    for aq in sorted_aqs:
        q = aq.question
        # Créer un dictionnaire id -> Option pour réordonner selon option_order
        options_dict = {opt.id: opt for opt in q.options}
        ordered_options = []
        for opt_id in aq.option_order:
            if opt_id in options_dict:
                opt = options_dict[opt_id]
                ordered_options.append(StudentOption(id=opt.id, text=opt.text))

        # Vérifier si question à choix multiple (plusieurs options correctes)
        correct_count = sum(1 for opt in q.options if opt.is_correct)
        is_multiple = correct_count > 1

        questions_out.append(
            StudentQuestion(
                id=q.id,
                position=aq.position,
                statement=q.statement,
                difficulty=q.difficulty,
                chapter=q.chapter,
                is_multiple_choice=is_multiple,
                options=ordered_options,
            )
        )

    # Charger les réponses sauvegardées existantes
    saved_answers = {
        ans.question_id: ans.selected_option_ids for ans in attempt.answers
    }

    return StudentAttemptTake(
        attempt_id=attempt.id,
        session_id=sess.id,
        quiz_subject=sess.quiz.subject if sess.quiz else "Examen",
        status=attempt.status,
        started_at=attempt.started_at,
        deadline_at=attempt.deadline_at,
        remaining_seconds=remaining,
        questions=questions_out,
        saved_answers=saved_answers,
    )


@router.put("/{attempt_id}/answers")
def save_answers(
    attempt_id: int,
    data: SaveAnswersRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sauvegarde automatique périodique (autosave) des réponses d'un étudiant."""
    attempt = db.get(Attempt, attempt_id)
    if not attempt:
        raise HTTPException(status_code=404, detail="Tentative introuvable")

    if current_user.role == "student" and attempt.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès non autorisé")

    if attempt.status != "IN_PROGRESS":
        raise HTTPException(status_code=400, detail="La copie n'est plus en cours de passation")

    now = get_current_utc()
    # Tolérance de 15 secondes pour latence réseau
    grace_period = timedelta(seconds=15)
    attempt_deadline = ensure_utc(attempt.deadline_at)
    if attempt_deadline and now > (attempt_deadline + grace_period):
        sess = db.get(ExamSession, attempt.session_id)
        if sess:
            submit_and_score_attempt(db, attempt, sess)
            db.commit()
        raise HTTPException(status_code=400, detail="Temps écoulé, réponses refusées")

    # Mettre à jour les réponses
    existing_answers = {
        ans.question_id: ans
        for ans in db.scalars(select(Answer).where(Answer.attempt_id == attempt.id)).all()
    }

    for q_id, opt_ids in data.answers.items():
        if q_id in existing_answers:
            existing_answers[q_id].selected_option_ids = opt_ids
        else:
            db.add(
                Answer(
                    attempt_id=attempt.id,
                    question_id=q_id,
                    selected_option_ids=opt_ids,
                )
            )

    db.commit()
    return {"status": "saved", "updated_at": now.isoformat()}


@router.post("/{attempt_id}/submit", response_model=SubmitResponse)
def submit_attempt(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soumission manuelle finale de la copie par l'étudiant."""
    attempt = db.scalar(
        select(Attempt)
        .where(Attempt.id == attempt_id)
        .options(
            joinedload(Attempt.session),
            selectinload(Attempt.attempt_questions),
        )
    )
    if not attempt:
        raise HTTPException(status_code=404, detail="Tentative introuvable")

    if current_user.role == "student" and attempt.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès non autorisé")

    if attempt.status != "IN_PROGRESS":
        raise HTTPException(status_code=400, detail="Cette copie n'est pas en cours de passation")

    submit_and_score_attempt(db, attempt, attempt.session)
    db.commit()

    return SubmitResponse(
        attempt_id=attempt.id,
        status=attempt.status,
        submitted_at=attempt.submitted_at,
        message="Copie soumise avec succès",
    )


@router.get("/{attempt_id}/review", response_model=AttemptReview)
def get_attempt_review(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Consultation de la correction détaillée avec notes, bonnes réponses et explications."""
    attempt = db.scalar(
        select(Attempt)
        .where(Attempt.id == attempt_id)
        .options(
            joinedload(Attempt.student),
            joinedload(Attempt.session).joinedload(ExamSession.quiz),
            selectinload(Attempt.attempt_questions).joinedload(AttemptQuestion.question).selectinload(Question.options),
            selectinload(Attempt.answers),
        )
    )
    if not attempt:
        raise HTTPException(status_code=404, detail="Tentative introuvable")

    # Droits : prof/admin OU l'étudiant lui-même si la copie est notée ou la session fermée
    sess = attempt.session
    is_teacher = current_user.role in ("teacher", "admin")
    is_owner_student = current_user.role == "student" and attempt.student_id == current_user.id

    if not is_teacher and not is_owner_student:
        raise HTTPException(status_code=403, detail="Accès refusé")

    if is_owner_student and attempt.status not in ("SUBMITTED", "GRADED"):
        raise HTTPException(status_code=400, detail="La copie n'a pas encore été soumise")

    answers_map = {ans.question_id: ans.selected_option_ids for ans in attempt.answers}
    sorted_aqs = sorted(attempt.attempt_questions, key=lambda x: x.position)

    review_questions: list[ReviewQuestion] = []
    total_max = len(sorted_aqs) * sess.points_per_question

    for aq in sorted_aqs:
        q = aq.question
        user_selected = answers_map.get(q.id, [])
        options_dict = {opt.id: opt for opt in q.options}

        review_opts = []
        for opt_id in aq.option_order:
            if opt_id in options_dict:
                opt = options_dict[opt_id]
                review_opts.append(
                    ReviewOption(
                        id=opt.id,
                        text=opt.text,
                        is_correct=opt.is_correct,
                        was_selected=(opt.id in user_selected),
                    )
                )

        q_score = compute_question_score(
            question=q,
            selected_option_ids=user_selected,
            points_per_question=sess.points_per_question,
            scoring_rule=sess.scoring_rule,
            penalty=sess.penalty,
        )

        review_questions.append(
            ReviewQuestion(
                question_id=q.id,
                position=aq.position,
                statement=q.statement,
                difficulty=q.difficulty,
                chapter=q.chapter,
                explanation=q.explanation,
                options=review_opts,
                score_earned=q_score,
                max_score=sess.points_per_question,
            )
        )

    return AttemptReview(
        attempt_id=attempt.id,
        session_id=sess.id,
        student_id=attempt.student_id,
        student_name=attempt.student.name if attempt.student else "Étudiant",
        student_email=attempt.student.email if attempt.student else "",
        status=attempt.status,
        started_at=attempt.started_at,
        submitted_at=attempt.submitted_at,
        auto_score=attempt.auto_score,
        final_score=attempt.final_score,
        teacher_comment=attempt.teacher_comment,
        total_max_score=total_max,
        questions=review_questions,
    )


@router.patch("/{attempt_id}/grade", response_model=AttemptReview)
def grade_attempt(
    attempt_id: int,
    data: AttemptGradeUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(teacher_or_admin),
):
    """Validation ou ajustement de la note finale et du commentaire par le professeur."""
    attempt = db.scalar(
        select(Attempt)
        .where(Attempt.id == attempt_id)
        .options(
            joinedload(Attempt.session).joinedload(ExamSession.quiz),
        )
    )
    if not attempt:
        raise HTTPException(status_code=404, detail="Tentative introuvable")

    if user.role != "admin" and attempt.session.quiz.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="Accès non autorisé")

    old_score = attempt.final_score
    attempt.final_score = data.final_score
    attempt.teacher_comment = data.teacher_comment
    attempt.status = "GRADED"

    db.add(
        AuditLog(
            user_id=user.id,
            action="GRADE_ATTEMPT",
            details=f"Copie {attempt.id} notée. Note modifiée de {old_score} à {data.final_score}. Commentaire : {data.teacher_comment or 'Aucun'}",
        )
    )
    db.commit()

    return get_attempt_review(attempt_id, db, user)
