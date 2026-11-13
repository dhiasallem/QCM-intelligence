try:
    from mistralai import Mistral
except ImportError:
    from mistralai.client import Mistral

from app.config import settings
from app.services.ai.base import QuestionGenerator


class MistralGenerator(QuestionGenerator):
    name = "mistral"

    def __init__(self):
        self.client = Mistral(api_key=settings.mistral_api_key)

    def generate(self, prompt: str) -> str:
        response = self.client.chat.complete(
            model=settings.mistral_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.7,
        )
        return response.choices[0].message.content or ""