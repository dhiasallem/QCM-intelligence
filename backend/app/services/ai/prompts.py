import math

POOL_FACTOR = 2  # banque = 2 fois le nombre demandé


def pool_size(nb_questions: int) -> int:
    return math.ceil(nb_questions * POOL_FACTOR)


def build_prompt(specialty: str, subject: str, level: str, nb_questions: int,
                 chapters: str | None = None) -> str:
    total = pool_size(nb_questions)
    n_facile = round(total * 0.3)
    n_difficile = round(total * 0.2)
    n_moyen = total - n_facile - n_difficile
    chapitres = f"\nChapitres à couvrir : {chapters}." if chapters else ""

    return f"""Tu es un enseignant expert. Rédige des questions à choix multiples (QCM) en français.

Contexte :
- Spécialité : {specialty}
- Matière : {subject}
- Niveau : {level}{chapitres}

Produis exactement {total} questions : {n_facile} faciles, {n_moyen} moyennes, {n_difficile} difficiles.

Règles :
- Chaque question a 4 propositions, dont au moins une correcte (une seule dans la majorité des cas).
- Les mauvaises propositions doivent être plausibles, jamais absurdes.
- Pas de « toutes les réponses ci-dessus » ni « aucune de ces réponses ».
- Aucune question en doublon ou quasi identique ; varie les chapitres et les notions.
- La réponse indiquée comme correcte doit être exacte et vérifiable.
- Donne une courte explication de la bonne réponse.

Réponds UNIQUEMENT avec un objet JSON valide, sans texte autour ni balises, au format :
{{"questions": [{{"enonce": "...", "difficulte": "facile|moyen|difficile", "chapitre": "...", "options": [{{"texte": "...", "correcte": true}}, {{"texte": "...", "correcte": false}}], "explication": "..."}}]}}"""