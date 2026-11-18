from app.db import SessionLocal
from app.models import Quiz, Question, Option, AiLog
from app.services.ai.orchestrator import generate_quiz, AllProvidersFailed


INTERRUPTED_MESSAGE = (
    "La génération a été interrompue (le serveur a redémarré pendant qu'elle était en cours). "
    "Cliquez sur « Relancer la génération »."
)


def recover_interrupted_generations(db) -> int:
    """À appeler au démarrage : les générations tournent dans le processus du serveur,
    donc toute banque encore « GENERATING » à ce moment-là a été interrompue et ne se
    terminera jamais. On la passe en échec pour qu'elle puisse être relancée ou supprimée."""
    stuck = db.query(Quiz).filter(Quiz.status == "GENERATING").all()
    for quiz in stuck:
        quiz.status = "FAILED"
        quiz.error = INTERRUPTED_MESSAGE
    db.commit()
    return len(stuck)


def run_generation(quiz_id: int) -> None:
    """Tâche de fond : appelle l'IA et enregistre la banque de questions."""
    with SessionLocal() as db:
        quiz = db.get(Quiz, quiz_id)
        if not quiz:
            return

        try:
            result = generate_quiz(
                quiz.specialty, quiz.subject, quiz.level,
                quiz.nb_questions, quiz.chapters,
            )
        except AllProvidersFailed as e:
            for a in e.attempts:
                db.add(AiLog(quiz_id=quiz.id, provider=a.provider, success=a.success,
                             duration_ms=a.duration_ms, error=a.error))
            quiz.status = "FAILED"
            quiz.error = str(e)[:1000]
            db.commit()
            return
        except Exception as e:  # noqa: BLE001
            quiz.status = "FAILED"
            quiz.error = str(e)[:1000]
            db.commit()
            return

        for old in list(quiz.questions):
            db.delete(old)
        db.flush()

        for q in result.quiz.questions:
            question = Question(
                quiz_id=quiz.id,
                statement=q.enonce.strip(),
                difficulty=q.difficulte,
                chapter=q.chapitre.strip() or None,
                explanation=q.explication.strip() or None,
                status="GENERATED",
            )
            question.options = [
                Option(text=o.texte.strip(), is_correct=o.correcte) for o in q.options
            ]
            db.add(question)

        for a in result.attempts:
            db.add(AiLog(quiz_id=quiz.id, provider=a.provider, success=a.success,
                         duration_ms=a.duration_ms, error=a.error))

        quiz.provider = result.provider
        quiz.status = "DRAFT"
        quiz.error = None
        db.commit()