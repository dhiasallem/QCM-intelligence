from google import genai
from app.config import settings

client = genai.Client(api_key=settings.gemini_api_key)
for m in client.models.list():
    if "generateContent" in (m.supported_actions or []):
        print(m.name)