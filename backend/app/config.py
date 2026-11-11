from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    redis_url: str
    jwt_secret: str
    gemini_api_key: str = ""
    gemini_model: str = ""
    mistral_api_key: str = ""
    ai_provider_order: str = "gemini,mistral"

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

settings = Settings()