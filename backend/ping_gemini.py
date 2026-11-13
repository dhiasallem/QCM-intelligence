import sys
import time

from google import genai
from google.genai import types

from app.config import settings

sys.stdout.reconfigure(encoding="utf-8")

client = genai.Client(
    api_key=settings.gemini_api_key,
    http_options=types.HttpOptions(timeout=60_000),
)

modeles = sys.argv[1:] or [settings.gemini_model]

for modele in modeles:
    debut = time.monotonic()
    try:
        r = client.models.generate_content(
            model=modele, contents="Réponds uniquement par le mot : OK"
        )
        print(f"OK     {modele:28} {time.monotonic() - debut:5.1f} s  -> {r.text.strip()[:20]}")
    except Exception as e:
        message = str(e).replace("\n", " ")[:90]
        print(f"ECHEC  {modele:28} {time.monotonic() - debut:5.1f} s  -> {message}")