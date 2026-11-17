"""Database / Supabase access (server-side only)."""

from spotify_pipeline.db.connection import SupabaseConfigError, get_supabase_client

__all__ = ["SupabaseConfigError", "get_supabase_client"]
