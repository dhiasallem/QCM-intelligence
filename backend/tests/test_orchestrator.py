import json
import re

import pytest

from app.services.ai import orchestrator
from app.services.ai.orchestrator import (
    AllProvidersFailed, batch_counts, generate_quiz, is_transient, parse_questions,
)

OVERLOADED = "503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand.'}}"


def make_question(label, difficulty="moyen"):
    return {
        "enonce": f"Question unique {label} ?",
        "difficulte": difficulty,
        "chapitre": "Chap",
        "explication": "Parce que.",
        "options": [
            {"texte": "Oui", "correcte": True},
            {"texte": "Non", "correcte": False},
            {"texte": "Peut-être", "correcte": False},
            {"texte": "Jamais", "correcte": False},
        ],
    }


def answer_for(prompt, start):
    """Répond exactement à la demande du prompt (nombre et difficultés), avec des énoncés uniques."""
    m = re.search(r"(\d+) faciles, (\d+) moyennes, (\d+) difficiles", prompt)
    f, mo, d = (int(x) for x in m.groups())
    diffs = ["facile"] * f + ["moyen"] * mo + ["difficile"] * d
    return json.dumps({"questions": [make_question(start + i, diff) for i, diff in enumerate(diffs)]})


class FakeProvider:
    """outcomes : liste de "ok" (répond correctement), d'exceptions ou de textes bruts."""

    def __init__(self, name, outcomes=None, default="ok"):
        self.name = name
        self.outcomes = list(outcomes or [])
        self.default = default
        self.prompts = []
        self.produced = 0

    def generate(self, prompt):
        self.prompts.append(prompt)
        out = self.outcomes.pop(0) if self.outcomes else self.default
        if isinstance(out, Exception):
            raise out
        if out == "ok":
            text = answer_for(prompt, start=self.produced + 1000 * len(self.prompts))
            self.produced += len(json.loads(text)["questions"])
            return text
        return out


@pytest.fixture
def sleeps(monkeypatch):
    recorded = []
    monkeypatch.setattr(orchestrator.time, "sleep", lambda s: recorded.append(s))
    return recorded


def use(monkeypatch, *providers):
    monkeypatch.setattr(orchestrator, "get_providers", lambda: list(providers))


def test_is_transient():
    assert is_transient(OVERLOADED)
    assert is_transient("429 RESOURCE_EXHAUSTED")
    assert is_transient("504 DEADLINE_EXCEEDED")
    assert not is_transient("seulement 3 questions valides sur 5 demandées")
    assert not is_transient(None)


def test_large_quiz_is_generated_in_batches(monkeypatch, sleeps):
    gemini = FakeProvider("gemini")
    use(monkeypatch, gemini)
    result = generate_quiz("Info", "Algo", "L1", 20)  # banque de 40 questions
    assert len(result.quiz.questions) == 40
    assert len(gemini.prompts) == 4
    assert all("exactement 10 questions" in p for p in gemini.prompts)
    # Les lots suivants rappellent les questions déjà produites
    assert "existent déjà" not in gemini.prompts[0]
    assert "existent déjà" in gemini.prompts[1]
    # Répartition globale 30/50/20 respectée
    diffs = [q.difficulte for q in result.quiz.questions]
    assert (diffs.count("facile"), diffs.count("moyen"), diffs.count("difficile")) == (12, 20, 8)
    assert sleeps == []


def test_invalid_question_is_dropped_not_whole_answer():
    bad = make_question("mauvaise")
    bad["options"][1]["texte"] = "Oui"  # options dupliquées -> invalide
    raw = json.dumps({"questions": [make_question("a"), bad, make_question("b")]})
    assert [q.enonce for q in parse_questions(raw)] == ["Question unique a ?", "Question unique b ?"]


def test_retries_with_backoff_after_overload_then_succeeds(monkeypatch, sleeps):
    gemini = FakeProvider("gemini", [Exception(OVERLOADED), Exception(OVERLOADED), "ok"])
    use(monkeypatch, gemini)
    result = generate_quiz("Info", "Algo", "L1", 2)
    assert result.provider == "gemini" and len(result.quiz.questions) == 4
    assert sleeps == [5, 15]


def test_falls_back_to_mistral(monkeypatch, sleeps):
    gemini = FakeProvider("gemini", default=Exception(OVERLOADED))
    mistral = FakeProvider("mistral")
    use(monkeypatch, gemini, mistral)
    result = generate_quiz("Info", "Algo", "L1", 2)
    assert result.provider == "mistral"
    assert [a.success for a in result.attempts] == [False, False, False, True]


def test_keeps_partial_bank_if_enough_questions(monkeypatch, sleeps):
    # 20 demandées -> banque de 40 ; 2 lots réussissent (20 questions) puis panne totale
    gemini = FakeProvider("gemini", ["ok", "ok"], default=Exception(OVERLOADED))
    use(monkeypatch, gemini)
    result = generate_quiz("Info", "Algo", "L1", 20)
    assert len(result.quiz.questions) == 20


def test_fails_if_not_enough_questions(monkeypatch, sleeps):
    gemini = FakeProvider("gemini", ["ok"], default=Exception(OVERLOADED))
    use(monkeypatch, gemini)
    with pytest.raises(AllProvidersFailed) as exc:
        generate_quiz("Info", "Algo", "L1", 20)
    msg = str(exc.value)
    assert msg.startswith("Le service d'IA (gemini) est saturé")
    assert "10 question(s) valide(s) obtenue(s) sur les 20 nécessaires" in msg
    assert "MISTRAL_API_KEY" in msg
    assert len(gemini.prompts) == 1 + 3  # le lot en panne n'est pas suivi d'autres lots


def test_duplicates_across_batches_are_topped_up(monkeypatch, sleeps):
    same = json.dumps({"questions": [make_question(i) for i in range(4)]})
    gemini = FakeProvider("gemini", [same, same])  # le 2e lot ne fait que des doublons
    use(monkeypatch, gemini)
    result = generate_quiz("Info", "Algo", "L1", 4)  # banque de 8
    assert len(result.quiz.questions) == 8
    assert len({q.enonce for q in result.quiz.questions}) == 8


def test_non_transient_error_uses_short_pause(monkeypatch, sleeps):
    gemini = FakeProvider("gemini", ["pas du json", "pas du json", "ok"])
    use(monkeypatch, gemini)
    generate_quiz("Info", "Algo", "L1", 2)
    assert sleeps == [2, 2]


def test_batch_counts():
    assert batch_counts(10, {"facile": 12, "moyen": 20, "difficile": 8}) == {"facile": 3, "moyen": 5, "difficile": 2}
    assert sum(batch_counts(7, {"facile": 1, "moyen": 0, "difficile": 0}).values()) == 7
