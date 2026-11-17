"""Postgres connection helper for Supabase (pg8000 + SUPABASE_DB_URL)."""

from __future__ import annotations

from urllib.parse import unquote, urlparse

from spotify_pipeline.config import Settings, get_settings


class PostgresConfigError(RuntimeError):
    """Raised when SUPABASE_DB_URL is missing or invalid."""


def require_db_url(settings: Settings | None = None) -> str:
    s = settings or get_settings()
    db_url = (s.supabase_db_url or "").strip()
    if not db_url:
        raise PostgresConfigError(
            "Set SUPABASE_DB_URL in .env (Dashboard → Database → Connect). "
            "Do not commit the URI."
        )
    return db_url


def connect_postgres(db_url: str | None = None):
    """Return a pg8000.native.Connection (caller must close)."""
    import pg8000.native

    url = db_url or require_db_url()
    parsed = urlparse(url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise PostgresConfigError("SUPABASE_DB_URL must be a postgresql:// URI")
    return pg8000.native.Connection(
        user=unquote(parsed.username or ""),
        password=unquote(parsed.password or ""),
        host=parsed.hostname or "",
        port=parsed.port or 5432,
        database=(parsed.path or "/postgres").lstrip("/") or "postgres",
        ssl_context=True,
    )
