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
    # Comma-separated Supabase Auth UUIDs allowed to edit shared reference constraints.
    admin_user_ids: str = ""
    # Server-side only. Never expose these values to web/frontend code.
    baltic_exchange_api_key: str | None = None
    baltic_exchange_feed_id: str | None = None
    baltic_exchange_api_version: str = "v1.3"
    baltic_exchange_api_base_url: str = "https://api.balticexchange.com"
    baltic_exchange_route_map_json: str | None = None
    baltic_exchange_state_file: str | None = None

    model_config = SettingsConfigDict(
        env_file=(str(ENV_FILE), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
