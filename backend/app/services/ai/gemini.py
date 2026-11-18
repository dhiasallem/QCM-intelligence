from google import genai
from google.genai import types

from app.config import settings
from app.services.ai.base import QuestionGenerator, QuizOut


class GeminiGenerator(QuestionGenerator):
    name = "gemini"

    def __init__(self):
        self.client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(timeout=120_000),  # 120 secondes
        )

    def generate(self, prompt: str) -> str:
        # Modèles à essayer en cas de 503 (forte demande temporaire)
        primary_model = settings.gemini_model or "gemini-3.5-flash"
        fallback_models = [primary_model]
        if "gemini-3.5-flash-lite" not in fallback_models:
            fallback_models.append("gemini-3.5-flash-lite")

        last_error = None
        for model_name in fallback_models:
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=QuizOut,
                        temperature=0.7,
                    ),
                )
                if response.text:
                    return response.text
            except Exception as e:
                last_error = e
                # Si erreur 503 (haute demande) ou temporaire, essayer le modèle suivant
                continue

        if last_error:
            raise last_error
        return ""
