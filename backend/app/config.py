from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"

class Settings(BaseSettings):
    database_url: str
    redis_url: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    gemini_api_key: str = ""
    gemini_model: str = ""
    mistral_api_key: str = ""
    mistral_model: str = "mistral-small-latest"
    ai_provider_order: str = "gemini,mistral"

    model_config = SettingsConfigDict(
        env_file=(str(ENV_PATH), "../.env", ".env"),
        extra="ignore",
    )

settings = Settings()