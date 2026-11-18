import random
from typing import Sequence
from app.models.quiz import Question


def stratified_sample(
    questions: Sequence[Question],
    nb_draw: int,
    seed: str,
) -> list[dict]:
    """Tire nb_draw questions de façon stratifiée et déterministe selon un seed.
    
    Retourne une liste d'éléments avec :
      - question_id : id de la question
      - position : 1..N
      - option_order : liste des ids des propositions mélangés
    """
    if len(questions) < nb_draw:
        raise ValueError(
            f"Banque insuffisante : {len(questions)} questions disponibles pour {nb_draw} demandées"
        )

    rng = random.Random(seed)

    # Répartir les questions par difficulté
    faciles = [q for q in questions if q.difficulty == "facile"]
    moyens = [q for q in questions if q.difficulty == "moyen"]
    difficiles = [q for q in questions if q.difficulty == "difficile"]
    autres = [q for q in questions if q.difficulty not in ("facile", "moyen", "difficile")]

    # Quotas cibles (30% facile, 50% moyen, 20% difficile)
    target_facile = round(nb_draw * 0.30)
    target_difficile = round(nb_draw * 0.20)
    target_moyen = nb_draw - target_facile - target_difficile

    selected: list[Question] = []

    def pick_from_pool(pool: list[Question], count: int) -> list[Question]:
        if not pool or count <= 0:
            return []
        shuffled = list(pool)
        rng.shuffle(shuffled)
        return shuffled[:count]

    picked_f = pick_from_pool(faciles, min(len(faciles), target_facile))
    picked_m = pick_from_pool(moyens, min(len(moyens), target_moyen))
    picked_d = pick_from_pool(difficiles, min(len(difficiles), target_difficile))

    selected.extend(picked_f)
    selected.extend(picked_m)
    selected.extend(picked_d)

    # Compléter si un panier manquait de questions
    remaining_needed = nb_draw - len(selected)
    if remaining_needed > 0:
        used_ids = {q.id for q in selected}
        remaining_pool = [q for q in questions if q.id not in used_ids]
        rng.shuffle(remaining_pool)
        selected.extend(remaining_pool[:remaining_needed])

    # Mélanger l'ordre des questions pour cet étudiant
    rng.shuffle(selected)

    result = []
    for pos, q in enumerate(selected, start=1):
        # Mélanger l'ordre des options
        option_ids = [opt.id for opt in q.options]
        rng.shuffle(option_ids)
        result.append({
            "question_id": q.id,
            "position": pos,
            "option_order": option_ids,
        })

    return result
