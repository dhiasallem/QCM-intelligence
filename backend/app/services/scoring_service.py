from typing import Sequence
from app.models.quiz import Question


def compute_question_score(
    question: Question,
    selected_option_ids: Sequence[int],
    points_per_question: float = 1.0,
    scoring_rule: str = "ALL_OR_NOTHING",
    penalty: float = 0.0,
) -> float:
    """Calcule la note d'une question selon la règle configurée."""
    correct_ids = {opt.id for opt in question.options if opt.is_correct}
    all_ids = {opt.id for opt in question.options}
    selected_ids = set(selected_option_ids) & all_ids  # Filtrer d'éventuels ids invalides

    if not correct_ids:
        return 0.0

    if scoring_rule == "ALL_OR_NOTHING":
        if selected_ids == correct_ids:
            return float(points_per_question)
        return 0.0

    elif scoring_rule == "PARTIAL":
        # Points proportionnels pour chaque bonne réponse trouvée, sans pénalité pour mauvaise réponse
        # mais une mauvaise réponse annule le point de proportion si spécifié ou réduit proportionnellement
        c_total = len(correct_ids)
        c_correct = len(selected_ids & correct_ids)
        c_incorrect = len(selected_ids - correct_ids)

        # Règle standard partielle : chaque bonne réponse donne (1/c_total), chaque mauvaise réponse enlève (1/c_total)
        # Bounded à [0, points_per_question]
        ratio = (c_correct - c_incorrect) / c_total
        ratio = max(0.0, min(1.0, ratio))
        return round(ratio * points_per_question, 2)

    elif scoring_rule == "PARTIAL_PENALTY":
        # Chaque bonne réponse donne sa part, chaque mauvaise réponse applique la pénalité configurée
        c_total = len(correct_ids)
        c_correct = len(selected_ids & correct_ids)
        c_incorrect = len(selected_ids - correct_ids)

        score = (c_correct / c_total) * points_per_question - (c_incorrect * penalty)
        score = max(0.0, min(points_per_question, score))
        return round(score, 2)

    return 0.0


def compute_attempt_score(
    questions: Sequence[Question],
    answers_map: dict[int, list[int]],
    points_per_question: float = 1.0,
    scoring_rule: str = "ALL_OR_NOTHING",
    penalty: float = 0.0,
) -> float:
    """Calcule le score total d'une tentative."""
    total = 0.0
    for q in questions:
        selected = answers_map.get(q.id, [])
        total += compute_question_score(
            q,
            selected,
            points_per_question=points_per_question,
            scoring_rule=scoring_rule,
            penalty=penalty,
        )
    return round(total, 2)
