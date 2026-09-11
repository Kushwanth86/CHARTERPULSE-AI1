from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# <repo>/services/api/app/config/settings.py -> repository root
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
ENV_FILE = REPOSITORY_ROOT / ".env"


class Settings(BaseSettings):
    app_name: str = "CHARTERPULSE AI API"
    app_version: str = "0.1.0"
    environment: str = "development"

    supabase_url: str | None = None
    supabase_publishable_key: str | None = None
    supabase_secret_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=(str(ENV_FILE), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
