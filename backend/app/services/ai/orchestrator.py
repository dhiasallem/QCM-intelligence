import re
import time
from dataclasses import dataclass, field

from app.config import settings
from app.services.ai.base import QuestionGenerator, QuizOut
from app.services.ai.prompts import build_prompt

MAX_ATTEMPTS_PER_PROVIDER = 2


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
    def __init__(self, attempts: list[AiAttempt]):
        self.attempts = attempts
        details = "; ".join(f"{a.provider}: {a.error}" for a in attempts)
        super().__init__(f"Tous les fournisseurs IA ont échoué ({details})")


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
    return text


def remove_duplicates(quiz: QuizOut) -> QuizOut:
    seen, unique = set(), []
    for q in quiz.questions:
        key = re.sub(r"\W+", " ", q.enonce.lower()).strip()
        if key not in seen:
            seen.add(key)
            unique.append(q)
    return QuizOut(questions=unique)


def generate_quiz(specialty: str, subject: str, level: str, nb_questions: int,
                  chapters: str | None = None) -> GenerationResult:
    prompt = build_prompt(specialty, subject, level, nb_questions, chapters)
    attempts: list[AiAttempt] = []

    providers = get_providers()
    if not providers:
        raise RuntimeError("Aucun fournisseur IA configuré (vérifiez .env)")

    for provider in providers:
        for _ in range(MAX_ATTEMPTS_PER_PROVIDER):
            start = time.monotonic()
            try:
                raw = provider.generate(prompt)
                quiz = QuizOut.model_validate_json(clean_json(raw))
                quiz = remove_duplicates(quiz)
                if len(quiz.questions) < nb_questions:
                    raise ValueError(
                        f"seulement {len(quiz.questions)} questions valides sur {nb_questions} demandées"
                    )
                ms = int((time.monotonic() - start) * 1000)
                attempts.append(AiAttempt(provider.name, True, ms))
                return GenerationResult(quiz=quiz, provider=provider.name, attempts=attempts)
            except Exception as e:  # noqa: BLE001
                ms = int((time.monotonic() - start) * 1000)
                attempts.append(AiAttempt(provider.name, False, ms, str(e)[:300]))

    raise AllProvidersFailed(attempts)