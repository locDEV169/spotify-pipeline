"""Supabase client factory (SPEC: SUPABASE_URL + SERVICE_ROLE).

Docs: https://supabase.com/docs/reference/python/initializing

Server/scripts only — service_role bypasses RLS. Do not use in browser/FE.
This slice only builds the client; no DDL / Bronze upload yet.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from supabase import Client, create_client

from spotify_pipeline.config import Settings, get_settings

if TYPE_CHECKING:
    pass


class SupabaseConfigError(RuntimeError):
    """Raised when Supabase URL / service_role key are missing."""


def get_supabase_client(settings: Settings | None = None) -> Client:
    """Create a sync Supabase client from Settings / `.env`.

    Requires:
    - SUPABASE_URL
    - SUPABASE_SERVICE_ROLE_KEY
    """
    s = settings or get_settings()
    url = (s.supabase_url or "").strip()
    key = (s.supabase_service_role_key or "").strip()
    if not url or not key:
        raise SupabaseConfigError(
            "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env "
            "(see .env.example). Service role is server-only."
        )
    return create_client(url, key)
