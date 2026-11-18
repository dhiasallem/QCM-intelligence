import json
import math
import re
import time
from dataclasses import dataclass, field

from pydantic import ValidationError

from app.config import settings
from app.services.ai.base import QuestionGenerator, QuestionOut, QuizOut
from app.services.ai.prompts import build_prompt, difficulty_split, pool_size

MAX_ATTEMPTS_PER_PROVIDER = 3
# Pause (secondes) avant chaque nouvel essai. Les surcharges (503/429) durent souvent
# quelques secondes à quelques dizaines de secondes : on attend de plus en plus longtemps.
TRANSIENT_BACKOFF = [5, 15]
DEFAULT_BACKOFF = 2

# Les grosses banques sont demandées par lots : une réponse courte est plus rapide,
# moins souvent refusée en cas de forte charge, et un lot raté ne fait pas tout perdre.
BATCH_SIZE = 10
EXTRA_BATCHES = 2  # lots supplémentaires autorisés pour compléter (doublons, questions invalides)

TRANSIENT_MARKERS = ("503", "504", "unavailable", "429", "resource_exhausted", "overloaded",
                     "high demand", "rate limit", "timeout", "timed out", "deadline")


def is_transient(error: str | None) -> bool:
    """Erreur passagère côté fournisseur (surcharge, quota, délai) : réessayer a du sens."""
    return bool(error) and any(m in error.lower() for m in TRANSIENT_MARKERS)


@dataclass
class AiAttempt:
    provider: str
    success: bool
    duration_ms: int
    error: str | None = None


@dataclass
class GenerationResult:
    quiz: QuizOut
    provider: str
    attempts: list[AiAttempt] = field(default_factory=list)


class AllProvidersFailed(Exception):
    def __init__(self, attempts: list[AiAttempt], collected: int = 0, needed: int = 0):
        self.attempts = attempts
        failed = [a for a in attempts if not a.success]
        details = "; ".join(f"{a.provider}: {a.error}" for a in failed)
        providers = sorted({a.provider for a in failed})
        if failed and all(is_transient(a.error) for a in failed):
            summary = (
                f"Le service d'IA ({', '.join(providers)}) est saturé ou indisponible pour le moment. "
                "C'est généralement temporaire : réessayez dans quelques minutes."
            )
            if providers == ["gemini"]:
                summary += " Astuce : configurez MISTRAL_API_KEY dans .env pour activer le relais automatique vers Mistral."
        else:
            summary = "Tous les fournisseurs IA ont échoué."
        if needed:
            summary += f" ({collected} question(s) valide(s) obtenue(s) sur les {needed} nécessaires.)"
        super().__init__(f"{summary}\n\nDétails techniques : {details}")


def get_providers() -> list[QuestionGenerator]:
    providers: list[QuestionGenerator] = []
    for name in settings.ai_provider_order.split(","):
        name = name.strip().lower()
        if name == "gemini" and settings.gemini_api_key and settings.gemini_model:
            from app.services.ai.gemini import GeminiGenerator
            providers.append(GeminiGenerator())
        elif name == "mistral" and settings.mistral_api_key and settings.mistral_model:
            from app.services.ai.mistral import MistralGenerator
            providers.append(MistralGenerator())
    return providers


def clean_json(raw: str) -> str:
    text = raw.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1:
        text = text[start:end + 1]
    # Nettoyer les échappements invalides en standard JSON (ex: \' -> ')
    text = re.sub(r"\\'", "'", text)
    return text


def parse_questions(raw: str) -> list[QuestionOut]:
    """Valide chaque question séparément : une question mal formée est écartée
    au lieu de faire rejeter toute la réponse."""
    try:
        data = json.loads(clean_json(raw))
    except json.JSONDecodeError as e:
        raise ValueError(f"réponse JSON invalide ({e.msg})") from e
    items = data.get("questions", []) if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ValueError("format inattendu : liste 'questions' absente")

    valid = []
    for item in items:
        try:
            valid.append(QuestionOut.model_validate(item))
        except ValidationError:
            continue
    if not valid:
        raise ValueError("aucune question valide dans la réponse")
    return valid


def question_key(q: QuestionOut) -> str:
    return re.sub(r"\W+", " ", q.enonce.lower()).strip()


def remove_duplicates(quiz: QuizOut) -> QuizOut:
    seen, unique = set(), []
    for q in quiz.questions:
        key = question_key(q)
        if key not in seen:
            seen.add(key)
            unique.append(q)
    return QuizOut(questions=unique)


def batch_counts(size: int, missing: dict[str, int]) -> dict[str, int]:
    """Répartit `size` questions entre les difficultés encore manquantes, au prorata."""
    total_missing = sum(missing.values())
    if total_missing <= 0:
        return {"facile": 0, "moyen": size, "difficile": 0}
    counts = {d: math.floor(size * n / total_missing) for d, n in missing.items()}
    # Distribuer le reste aux difficultés les plus en manque
    for d in sorted(missing, key=lambda d: missing[d] - counts[d], reverse=True):
        if sum(counts.values()) >= size:
            break
        counts[d] += 1
    return counts


def generate_batch(providers: list[QuestionGenerator], prompt: str,
                   attempts: list[AiAttempt]) -> tuple[list[QuestionOut], str] | None:
    """Un lot : chaque fournisseur dans l'ordre, avec nouveaux essais. None si tout a échoué."""
    for provider in providers:
        for attempt_num in range(MAX_ATTEMPTS_PER_PROVIDER):
            if attempt_num > 0:
                last_error = attempts[-1].error
                if is_transient(last_error):
                    time.sleep(TRANSIENT_BACKOFF[min(attempt_num - 1, len(TRANSIENT_BACKOFF) - 1)])
                else:
                    time.sleep(DEFAULT_BACKOFF)
            start = time.monotonic()
            try:
                questions = parse_questions(provider.generate(prompt))
                ms = int((time.monotonic() - start) * 1000)
                attempts.append(AiAttempt(provider.name, True, ms))
                return questions, provider.name
            except Exception as e:  # noqa: BLE001
                ms = int((time.monotonic() - start) * 1000)
                attempts.append(AiAttempt(provider.name, False, ms, str(e)[:300]))
    return None


def generate_quiz(specialty: str, subject: str, level: str, nb_questions: int,
                  chapters: str | None = None) -> GenerationResult:
    """Génère une banque de `pool_size(nb_questions)` questions, lot par lot.

    Réussit dès qu'au moins `nb_questions` questions valides et distinctes ont été obtenues
    (le minimum pour valider le QCM), même si un lot échoue en cours de route.
    """
    providers = get_providers()
    if not providers:
        raise RuntimeError("Aucun fournisseur IA configuré (vérifiez .env)")

    target = pool_size(nb_questions)
    wanted = difficulty_split(target)
    max_batches = math.ceil(target / BATCH_SIZE) + EXTRA_BATCHES

    attempts: list[AiAttempt] = []
    collected: list[QuestionOut] = []
    seen: set[str] = set()
    used_providers: list[str] = []

    for _ in range(max_batches):
        remaining = target - len(collected)
        if remaining <= 0:
            break
        have = {d: sum(1 for q in collected if q.difficulte == d) for d in wanted}
        missing = {d: max(0, wanted[d] - have[d]) for d in wanted}
        prompt = build_prompt(
            specialty, subject, level,
            batch_counts(min(BATCH_SIZE, remaining), missing),
            chapters,
            avoid=[q.enonce for q in collected],
        )

        outcome = generate_batch(providers, prompt, attempts)
        if outcome is None:
            break  # tous les fournisseurs échouent : inutile d'insister sur les lots suivants
        questions, provider_name = outcome
        if provider_name not in used_providers:
            used_providers.append(provider_name)
        for q in questions:
            key = question_key(q)
            if key not in seen and len(collected) < target:
                seen.add(key)
                collected.append(q)

    if len(collected) < nb_questions:
        raise AllProvidersFailed(attempts, collected=len(collected), needed=nb_questions)

    return GenerationResult(
        quiz=QuizOut(questions=collected),
        provider="+".join(used_providers),
        attempts=attempts,
    )
