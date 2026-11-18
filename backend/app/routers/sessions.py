import csv
import io
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select, func
from sqlalchemy.orm import Session, selectinload, joinedload

from app.db import get_db
from app.deps import require_role
from app.models.exam import ExamSession, Attempt, AttemptQuestion, Answer, AuditLog
from app.models.quiz import Quiz, Question
from app.models.user import User, Group
from app.schemas.session import SessionCreate, SessionRead, SessionSummary
from app.schemas.attempt import TeacherAttemptItem
from app.services.sampling_service import stratified_sample
from app.services.scoring_service import compute_attempt_score

router = APIRouter(prefix="/sessions", tags=["sessions"])
teacher_or_admin = require_role("teacher", "admin")


def get_owned_session(db: Session, session_id: int, user: User) -> ExamSession:
    sess = db.scalar(
        select(ExamSession)
        .where(ExamSession.id == session_id)
        .options(
            joinedload(ExamSession.quiz),
            joinedload(ExamSession.group).selectinload(Group.students),
            selectinload(ExamSession.attempts).joinedload(Attempt.student),
        )
    )
    if not sess:
        raise HTTPException(status_code=404, detail="Session d'examen introuvable")

    if user.role != "admin" and sess.quiz.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="Accès non autorisé à cette session")

    return sess


def close_expired_sessions(db: Session, sessions: list[ExamSession]) -> None:
    """Passe en CLOSED les sessions ouvertes dont l'heure de clôture est dépassée,
    et soumet (avec calcul de la note) les copies restées en cours."""
    from app.routers.attempts import submit_and_score_attempt  # import local : évite un cycle

    now = datetime.now(timezone.utc)
    changed = False
    for s in sessions:
        closes_at = s.closes_at if s.closes_at.tzinfo else s.closes_at.replace(tzinfo=timezone.utc)
        if s.status == "OPEN" and closes_at <= now:
            s.status = "CLOSED"
            for a in s.attempts:
                if a.status == "IN_PROGRESS":
                    submit_and_score_attempt(db, a, s)
            changed = True
    if changed:
        db.commit()


def load_session_questions(db: Session, sess: ExamSession) -> list[Question]:
    """Questions valides (non annulées) de la banque d'une session, avec leurs options."""
    return list(db.scalars(
        select(Question)
        .where(Question.quiz_id == sess.quiz_id, Question.status != "REJECTED")
        .options(selectinload(Question.options))
    ).all())


def generate_attempts(
    db: Session, sess: ExamSession, students: list[User], questions: list[Question]
) -> int:
    """Crée une copie individualisée déterministe pour chaque étudiant qui n'en a pas encore.

    Retourne le nombre de copies créées. N'effectue pas de commit.
    """
    existing_student_ids = set(
        db.scalars(select(Attempt.student_id).where(Attempt.session_id == sess.id))
    )
    created = 0
    for student in students:
        if student.id in existing_student_ids:
            continue

        seed = f"{sess.id}_{student.id}"
        sampled = stratified_sample(
            questions=questions,
            nb_draw=sess.questions_per_student,
            seed=seed,
        )

        attempt = Attempt(
            session_id=sess.id,
            student_id=student.id,
            seed=seed,
            status="NOT_STARTED",
        )
        db.add(attempt)
        db.flush()  # Pour obtenir attempt.id

        for item in sampled:
            db.add(
                AttemptQuestion(
                    attempt_id=attempt.id,
                    question_id=item["question_id"],
                    position=item["position"],
                    option_order=item["option_order"],
                )
            )
        created += 1
    return created


@router.post("", response_model=SessionRead, status_code=status.HTTP_201_CREATED)
def create_session(
    data: SessionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(teacher_or_admin),
):
    quiz = db.scalar(
        select(Quiz)
        .where(Quiz.id == data.quiz_id)
        .options(selectinload(Quiz.questions))
    )
    if not quiz or (user.role != "admin" and quiz.teacher_id != user.id):
        raise HTTPException(status_code=404, detail="QCM introuvable")

    if quiz.status != "VALIDATED":
        raise HTTPException(
            status_code=400,
            detail="Le QCM doit être validé par le professeur avant de pouvoir créer une session",
        )

    valid_questions = [q for q in quiz.questions if q.status != "REJECTED"]
    if len(valid_questions) < data.questions_per_student:
        raise HTTPException(
            status_code=400,
            detail=f"La banque ne contient que {len(valid_questions)} questions valides, inférieur aux {data.questions_per_student} demandées par étudiant",
        )

    group = db.get(Group, data.group_id)
    if not group or (user.role != "admin" and group.teacher_id != user.id):
        raise HTTPException(status_code=404, detail="Groupe introuvable")

    session_obj = ExamSession(
        quiz_id=data.quiz_id,
        group_id=data.group_id,
        opens_at=data.opens_at,
        closes_at=data.closes_at,
        duration_minutes=data.duration_minutes,
        questions_per_student=data.questions_per_student,
        points_per_question=data.points_per_question,
        scoring_rule=data.scoring_rule,
        penalty=data.penalty,
        status="DRAFT",
    )
    db.add(session_obj)
    db.commit()
    db.refresh(session_obj)

    return SessionRead(
        id=session_obj.id,
        quiz_id=session_obj.quiz_id,
        group_id=session_obj.group_id,
        opens_at=session_obj.opens_at,
        closes_at=session_obj.closes_at,
        duration_minutes=session_obj.duration_minutes,
        questions_per_student=session_obj.questions_per_student,
        points_per_question=session_obj.points_per_question,
        scoring_rule=session_obj.scoring_rule,
        penalty=session_obj.penalty,
        status=session_obj.status,
        quiz_subject=quiz.subject,
        group_name=group.name,
        total_attempts=0,
        submitted_attempts=0,
    )


@router.get("", response_model=list[SessionSummary])
def list_sessions(
    db: Session = Depends(get_db),
    user: User = Depends(teacher_or_admin),
):
    query = (
        select(ExamSession)
        .options(
            joinedload(ExamSession.quiz),
            joinedload(ExamSession.group),
            selectinload(ExamSession.attempts),
        )
        .order_by(ExamSession.id.desc())
    )
    if user.role != "admin":
        query = query.join(Quiz).where(Quiz.teacher_id == user.id)

    sessions = db.scalars(query).all()
    close_expired_sessions(db, sessions)
    results = []
    for s in sessions:
        submitted = sum(1 for a in s.attempts if a.status in ("SUBMITTED", "GRADED"))
        results.append(
            SessionSummary(
                id=s.id,
                quiz_id=s.quiz_id,
                quiz_subject=s.quiz.subject if s.quiz else None,
                group_id=s.group_id,
                group_name=s.group.name if s.group else None,
                opens_at=s.opens_at,
                closes_at=s.closes_at,
                duration_minutes=s.duration_minutes,
                questions_per_student=s.questions_per_student,
                status=s.status,
                total_attempts=len(s.attempts),
                submitted_attempts=submitted,
            )
        )
    return results


@router.get("/{session_id}", response_model=SessionRead)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(teacher_or_admin),
):
    sess = get_owned_session(db, session_id, user)
    close_expired_sessions(db, [sess])
    submitted = sum(1 for a in sess.attempts if a.status in ("SUBMITTED", "GRADED"))
    return SessionRead(
        id=sess.id,
        quiz_id=sess.quiz_id,
        group_id=sess.group_id,
        opens_at=sess.opens_at,
        closes_at=sess.closes_at,
        duration_minutes=sess.duration_minutes,
        questions_per_student=sess.questions_per_student,
        points_per_question=sess.points_per_question,
        scoring_rule=sess.scoring_rule,
        penalty=sess.penalty,
        status=sess.status,
        quiz_subject=sess.quiz.subject if sess.quiz else None,
        group_name=sess.group.name if sess.group else None,
        total_attempts=len(sess.attempts),
        submitted_attempts=submitted,
    )


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: int,
    force: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(teacher_or_admin),
):
    """Supprime une session et toutes ses copies (réponses et notes comprises).

    Si des étudiants ont déjà commencé ou rendu leur copie, il faut passer force=true.
    """
    sess = get_owned_session(db, session_id, user)
    started = sum(1 for a in sess.attempts if a.status != "NOT_STARTED")
    if started and not force:
        raise HTTPException(
            status_code=409,
            detail=f"{started} copie(s) déjà commencée(s) ou rendue(s) : confirmez la suppression",
        )

    db.add(
        AuditLog(
            user_id=user.id,
            action="DELETE_SESSION",
            details=f"Session {sess.id} ({sess.quiz.subject if sess.quiz else '?'}) supprimée avec {len(sess.attempts)} copie(s), dont {started} commencée(s).",
        )
    )
    db.delete(sess)  # copies, questions tirées et réponses supprimées en cascade
    db.commit()


@router.post("/{session_id}/publish", response_model=SessionRead)
def publish_session(
    session_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(teacher_or_admin),
):
    """Génère les copies individuelles (tirage stratifié + ordre aléatoire) et ouvre la session."""
    sess = get_owned_session(db, session_id, user)
    if sess.status != "DRAFT":
        raise HTTPException(status_code=400, detail="La session est déjà publiée ou clôturée")

    quiz = sess.quiz
    if quiz.status != "VALIDATED":
        raise HTTPException(status_code=400, detail="Le QCM associé n'est pas validé")

    students = sess.group.students
    if not students:
        raise HTTPException(
            status_code=400,
            detail="Le groupe d'étudiants sélectionné est vide. Ajoutez des étudiants d'abord.",
        )

    questions = load_session_questions(db, sess)
    if len(questions) < sess.questions_per_student:
        raise HTTPException(
            status_code=400,
            detail=f"Questions insuffisantes ({len(questions)} valides pour {sess.questions_per_student} demandées)",
        )

    generate_attempts(db, sess, students, questions)

    sess.status = "OPEN"
    db.add(
        AuditLog(
            user_id=user.id,
            action="PUBLISH_SESSION",
            details=f"Session {sess.id} publiée avec {len(students)} copies individuelles.",
        )
    )
    db.commit()

    return get_session(session_id, db, user)


@router.get("/{session_id}/attempts", response_model=list[TeacherAttemptItem])
def list_session_attempts(
    session_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(teacher_or_admin),
):
    sess = get_owned_session(db, session_id, user)
    return [
        TeacherAttemptItem(
            id=a.id,
            student_id=a.student_id,
            student_name=a.student.name if a.student else "Inconnu",
            student_email=a.student.email if a.student else "",
            status=a.status,
            started_at=a.started_at,
            submitted_at=a.submitted_at,
            auto_score=a.auto_score,
            final_score=a.final_score,
            teacher_comment=a.teacher_comment,
        )
        for a in sess.attempts
    ]


@router.get("/{session_id}/export")
def export_session_results(
    session_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(teacher_or_admin),
):
    """Exporte les résultats de la session au format CSV."""
    sess = get_owned_session(db, session_id, user)

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "ID Copie",
        "Nom Étudiant",
        "Email",
        "Statut",
        "Début",
        "Fin/Soumission",
        "Note Automatique",
        "Note Finale",
        "Commentaire Professeur",
    ])

    for a in sess.attempts:
        writer.writerow([
            a.id,
            a.student.name if a.student else "",
            a.student.email if a.student else "",
            a.status,
            a.started_at.strftime("%Y-%m-%d %H:%M:%S") if a.started_at else "",
            a.submitted_at.strftime("%Y-%m-%d %H:%M:%S") if a.submitted_at else "",
            f"{a.auto_score:.2f}" if a.auto_score is not None else "",
            f"{a.final_score:.2f}" if a.final_score is not None else "",
            a.teacher_comment or "",
        ])

    output.seek(0)
    filename = f"resultats_session_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/{session_id}/cancel-question/{question_id}")
def cancel_question_in_session(
    session_id: int,
    question_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(teacher_or_admin),
):
    """Annule une question défectueuse et recalcule immédiatement les notes de tous les étudiants."""
    sess = get_owned_session(db, session_id, user)
    question = db.get(Question, question_id)
    if not question or question.quiz_id != sess.quiz_id:
        raise HTTPException(status_code=404, detail="Question non trouvée dans ce QCM")

    question.status = "REJECTED"

    # Recalculer les notes pour les copies soumises ou notées
    recalculated_count = 0
    for a in sess.attempts:
        if a.status in ("SUBMITTED", "GRADED"):
            # Charger les questions de l'étudiant à l'exception de celle annulée
            qs = (
                db.scalars(
                    select(Question)
                    .join(AttemptQuestion, AttemptQuestion.question_id == Question.id)
                    .where(
                        AttemptQuestion.attempt_id == a.id,
                        Question.id != question_id,
                    )
                    .options(selectinload(Question.options))
                )
                .all()
            )

            # Charger les réponses actuelles
            answers = db.scalars(
                select(Answer).where(Answer.attempt_id == a.id)
            ).all()
            ans_map = {ans.question_id: ans.selected_option_ids for ans in answers}

            new_auto = compute_attempt_score(
                questions=qs,
                answers_map=ans_map,
                points_per_question=sess.points_per_question,
                scoring_rule=sess.scoring_rule,
                penalty=sess.penalty,
            )
            a.auto_score = new_auto
            # Si aucune note manuelle spécifique n'avait été posée ou pour mettre à jour
            if a.status == "SUBMITTED":
                a.final_score = new_auto
            recalculated_count += 1

    db.add(
        AuditLog(
            user_id=user.id,
            action="CANCEL_QUESTION",
            details=f"Question {question_id} annulée dans la session {sess.id}. {recalculated_count} copies recalculées.",
        )
    )
    db.commit()

    return {
        "message": f"Question {question_id} annulée. {recalculated_count} copies ont été recalculées.",
    }
