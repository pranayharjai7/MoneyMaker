from __future__ import annotations

from functools import lru_cache
from typing import Any

from backend.core.config import Settings, get_settings


class SupabaseConfigurationError(RuntimeError):
    """Raised when Supabase credentials are missing or the client cannot be created."""


@lru_cache
def get_supabase_client() -> Any:
    settings = get_settings()
    return create_supabase_client(settings)


def create_supabase_client(settings: Settings) -> Any:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise SupabaseConfigurationError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be configured for backend writes."
        )

    try:
        from supabase import create_client
    except ImportError as exc:
        raise SupabaseConfigurationError(
            "The 'supabase' package is required. Install backend requirements first."
        ) from exc

    return create_client(settings.supabase_url, settings.supabase_service_role_key)

