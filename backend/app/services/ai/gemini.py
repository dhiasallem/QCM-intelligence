from google import genai
from google.genai import types

from app.config import settings
from app.services.ai.base import QuestionGenerator


class GeminiGenerator(QuestionGenerator):
    name = "gemini"

    def __init__(self):
        self.client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(timeout=90_000),  # 90 secondes
        )

    def generate(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.7,
            ),
        )
        return response.text or ""