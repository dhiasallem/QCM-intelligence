import pytest
from app.models.quiz import Question, Option
from app.services.scoring_service import compute_question_score, compute_attempt_score


def make_question(q_id: int, options_data: list[tuple[int, bool]]):
    q = Question(id=q_id, statement="Test question", difficulty="moyen")
    q.options = [
        Option(id=opt_id, question_id=q_id, text=f"Opt {opt_id}", is_correct=corr)
        for opt_id, corr in options_data
    ]
    return q


def test_scoring_all_or_nothing():
    # Options 1 (vraie), 2 (fausse), 3 (fausse), 4 (fausse)
    q = make_question(1, [(1, True), (2, False), (3, False), (4, False)])

    # Exacte
    assert compute_question_score(q, [1], points_per_question=2.0, scoring_rule="ALL_OR_NOTHING") == 2.0
    # Faux choix
    assert compute_question_score(q, [2], points_per_question=2.0, scoring_rule="ALL_OR_NOTHING") == 0.0
    # Bonne réponse + mauvaise réponse cochée
    assert compute_question_score(q, [1, 2], points_per_question=2.0, scoring_rule="ALL_OR_NOTHING") == 0.0
    # Aucune réponse
    assert compute_question_score(q, [], points_per_question=2.0, scoring_rule="ALL_OR_NOTHING") == 0.0


def test_scoring_multiple_choice_all_or_nothing():
    # 2 bonnes réponses (1 et 3)
    q = make_question(2, [(1, True), (2, False), (3, True), (4, False)])

    assert compute_question_score(q, [1, 3], points_per_question=1.0, scoring_rule="ALL_OR_NOTHING") == 1.0
    # Partiel en ALL_OR_NOTHING donne 0
    assert compute_question_score(q, [1], points_per_question=1.0, scoring_rule="ALL_OR_NOTHING") == 0.0
    assert compute_question_score(q, [1, 2, 3], points_per_question=1.0, scoring_rule="ALL_OR_NOTHING") == 0.0


def test_scoring_partial():
    # 2 bonnes réponses (1 et 2)
    q = make_question(3, [(1, True), (2, True), (3, False), (4, False)])

    # Plein score
    assert compute_question_score(q, [1, 2], points_per_question=2.0, scoring_rule="PARTIAL") == 2.0
    # Moitié des bonnes réponses
    assert compute_question_score(q, [1], points_per_question=2.0, scoring_rule="PARTIAL") == 1.0
    # 1 bonne et 1 mauvaise
    assert compute_question_score(q, [1, 3], points_per_question=2.0, scoring_rule="PARTIAL") == 0.0


def test_scoring_partial_penalty():
    # 2 bonnes réponses (1 et 2)
    q = make_question(4, [(1, True), (2, True), (3, False), (4, False)])

    # 1 bonne (donne 1.0) et 1 mauvaise avec pénalité de 0.5 -> 0.5
    score = compute_question_score(
        q, [1, 3], points_per_question=2.0, scoring_rule="PARTIAL_PENALTY", penalty=0.5
    )
    assert score == 0.5

    # Trop de mauvaises réponses ne donne pas une note négative (borné à 0.0)
    score_min = compute_question_score(
        q, [3, 4], points_per_question=2.0, scoring_rule="PARTIAL_PENALTY", penalty=1.0
    )
    assert score_min == 0.0
