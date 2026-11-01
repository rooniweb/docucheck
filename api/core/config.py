from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    litellm_base_url: str = "http://localhost:4000"
    litellm_api_key: str = "sk-docucheck"
    docling_base_url: str = "http://localhost:5001"
    database_url: str = "postgresql://docucheck:docucheck@localhost:5432/docucheck"

    llm_model: str = "ollama/mistral"
    confidence_threshold: float = 0.80

    # Contrôle des logs
    log_level: str = "INFO"


settings = Settings()
