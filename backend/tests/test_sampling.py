import pytest
from app.models.quiz import Question, Option
from app.services.sampling_service import stratified_sample


def build_mock_bank(total: int = 30):
    questions = []
    opt_counter = 1
    for i in range(1, total + 1):
        if i <= 10:
            diff = "facile"
        elif i <= 24:
            diff = "moyen"
        else:
            diff = "difficile"
        
        q = Question(
            id=i,
            statement=f"Question {i} test",
            difficulty=diff,
            chapter=f"Chapitre {(i % 3) + 1}",
            explanation=f"Explication {i}",
            status="GENERATED",
        )
        opts = []
        for o_idx in range(4):
            opts.append(Option(id=opt_counter, question_id=i, text=f"Opt {opt_counter}", is_correct=(o_idx == 0)))
            opt_counter += 1
        q.options = opts
        questions.append(q)
    return questions


def test_sampling_determinism():
    bank = build_mock_bank(30)
    seed = "session_10_student_42"

    draw_1 = stratified_sample(bank, nb_draw=10, seed=seed)
    draw_2 = stratified_sample(bank, nb_draw=10, seed=seed)

    # Même seed => résultat rigoureusement identique
    assert [d["question_id"] for d in draw_1] == [d["question_id"] for d in draw_2]
    assert [d["option_order"] for d in draw_1] == [d["option_order"] for d in draw_2]


def test_sampling_different_seeds():
    bank = build_mock_bank(30)
    seed_a = "session_10_student_1"
    seed_b = "session_10_student_2"

    draw_a = stratified_sample(bank, nb_draw=10, seed=seed_a)
    draw_b = stratified_sample(bank, nb_draw=10, seed=seed_b)

    order_a = [d["question_id"] for d in draw_a]
    order_b = [d["question_id"] for d in draw_b]

    # Des seeds différents doivent produire des tirages ou des ordres différents
    assert order_a != order_b


def test_sampling_stratification_and_counts():
    bank = build_mock_bank(30)
    draw = stratified_sample(bank, nb_draw=15, seed="test_seed_strat")

    assert len(draw) == 15
    q_map = {q.id: q for q in bank}

    drawn_questions = [q_map[d["question_id"]] for d in draw]
    faciles = [q for q in drawn_questions if q.difficulty == "facile"]
    moyens = [q for q in drawn_questions if q.difficulty == "moyen"]
    difficiles = [q for q in drawn_questions if q.difficulty == "difficile"]

    # 15 questions : 30% facile (4-5), 20% difficile (3), reste moyen (7-8)
    assert len(faciles) >= 3
    assert len(moyens) >= 5
    assert len(difficiles) >= 2


def test_options_integrity():
    bank = build_mock_bank(10)
    draw = stratified_sample(bank, nb_draw=5, seed="options_test_seed")

    q_map = {q.id: q for q in bank}
    for item in draw:
        q = q_map[item["question_id"]]
        original_option_ids = {opt.id for opt in q.options}
        shuffled_option_ids = set(item["option_order"])

        # Toutes les options doivent être présentes et sans doublons
        assert original_option_ids == shuffled_option_ids
        assert len(item["option_order"]) == len(original_option_ids)
