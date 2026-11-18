import math

POOL_FACTOR = 2  # banque = 2 fois le nombre demandé
DIFFICULTY_SHARES = {"facile": 0.3, "moyen": 0.5, "difficile": 0.2}
MAX_AVOID = 40  # nombre maximal d'énoncés déjà produits rappelés à l'IA


def pool_size(nb_questions: int) -> int:
    return math.ceil(nb_questions * POOL_FACTOR)


def difficulty_split(total: int) -> dict[str, int]:
    """Répartition cible de la banque : 30 % faciles, 50 % moyennes, 20 % difficiles."""
    n_facile = round(total * DIFFICULTY_SHARES["facile"])
    n_difficile = round(total * DIFFICULTY_SHARES["difficile"])
    return {"facile": n_facile, "moyen": total - n_facile - n_difficile, "difficile": n_difficile}


def build_prompt(specialty: str, subject: str, level: str, counts: dict[str, int],
                 chapters: str | None = None, avoid: list[str] | None = None) -> str:
    """Prompt pour UN lot de questions.

    `counts` : nombre de questions par difficulté pour ce lot.
    `avoid` : énoncés déjà générés dans les lots précédents (à ne pas répéter).
    """
    total = sum(counts.values())
    chapitres = f"\nChapitres à couvrir : {chapters}." if chapters else ""

    deja = ""
    if avoid:
        lignes = "\n".join(f"- {e[:120]}" for e in avoid[-MAX_AVOID:])
        deja = (
            "\n\nCes questions existent déjà dans la banque : n'en reprends aucune et ne les "
            f"reformule pas, aborde d'autres notions.\n{lignes}"
        )

    return f"""Tu es un enseignant expert. Rédige des questions à choix multiples (QCM) en français.

Contexte :
- Spécialité : {specialty}
- Matière : {subject}
- Niveau : {level}{chapitres}

Produis exactement {total} questions : {counts.get("facile", 0)} faciles, {counts.get("moyen", 0)} moyennes, {counts.get("difficile", 0)} difficiles.

Règles :
- Chaque question a 4 propositions, dont au moins une correcte (une seule dans la majorité des cas).
- Les 4 propositions d'une même question sont toutes différentes.
- Les mauvaises propositions doivent être plausibles, jamais absurdes.
- Pas de « toutes les réponses ci-dessus » ni « aucune de ces réponses ».
- Aucune question en doublon ou quasi identique ; varie les chapitres et les notions.
- La réponse indiquée comme correcte doit être exacte et vérifiable.
- Donne une courte explication de la bonne réponse.{deja}

Réponds UNIQUEMENT avec un objet JSON valide, sans texte autour ni balises, au format :
{{"questions": [{{"enonce": "...", "difficulte": "facile|moyen|difficile", "chapitre": "...", "options": [{{"texte": "...", "correcte": true}}, {{"texte": "...", "correcte": false}}], "explication": "..."}}]}}"""
