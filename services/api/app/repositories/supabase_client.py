from functools import lru_cache

from supabase import Client, create_client

from services.api.app.config.settings import get_settings


@lru_cache
def get_supabase_client() -> Client:
    """Return the normal Supabase client for public/read APIs."""
    settings = get_settings()

    if not settings.supabase_url or not settings.supabase_publishable_key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY are required for database access."
        )

    return create_client(
        settings.supabase_url,
        settings.supabase_publishable_key,
    )


@lru_cache
def get_supabase_admin_client() -> Client:
    """Return the privileged client for trusted server-side operations."""
    settings = get_settings()

    if not settings.supabase_url or not settings.supabase_secret_key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SECRET_KEY are required for privileged server-side operations."
        )

    return create_client(
        settings.supabase_url,
        settings.supabase_secret_key,
    )
