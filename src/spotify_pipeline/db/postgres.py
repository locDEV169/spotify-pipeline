"""Postgres connection helper for Supabase (pg8000 + SUPABASE_DB_URL)."""

from __future__ import annotations

import sys
from urllib.parse import unquote, urlparse

from spotify_pipeline.config import Settings, get_settings

# Transaction-mode pooler historically broke pg8000 *named* prepared statements.
_POOLER_TX_PORT = 6543
_WARNED_POOLER = False
_BIND_MISMATCH_HINT = (
    "Postgres prepared-statement error (08P01 / 26000) with pg8000. "
    "Prefer Session pooler …pooler.supabase.com:5432 in SUPABASE_DB_URL "
    "(Direct db.<ref>.supabase.co:5432 may time out on some networks)."
)


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


def is_prepare_bind_mismatch(exc: BaseException) -> bool:
    """True for pooler/prepared-statement failures (08P01, 26000, …)."""
    text = str(exc)
    return (
        "08P01" in text
        or "26000" in text
        or "bind message supplies" in text
        or "unnamed prepared statement does not exist" in text
    )


def connect_postgres(db_url: str | None = None):
    """Return a pg8000.native.Connection (caller must close)."""
    import pg8000.native

    global _WARNED_POOLER

    url = db_url or require_db_url()
    parsed = urlparse(url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise PostgresConfigError("SUPABASE_DB_URL must be a postgresql:// URI")
    port = parsed.port or 5432
    if port == _POOLER_TX_PORT and not _WARNED_POOLER:
        _WARNED_POOLER = True
        print(
            "WARN: SUPABASE_DB_URL uses port 6543 (transaction pooler). "
            "Bronze writers use simple SQL (no prepares). Still prefer Session "
            "pooler …pooler.supabase.com:5432 when possible.",
            file=sys.stderr,
        )
    return pg8000.native.Connection(
        user=unquote(parsed.username or ""),
        password=unquote(parsed.password or ""),
        host=parsed.hostname or "",
        port=port,
        database=(parsed.path or "/postgres").lstrip("/") or "postgres",
        ssl_context=True,
    )


def reconnect_postgres(db_url: str, old_conn=None):
    """Close old connection (ignore errors) and open a fresh one."""
    if old_conn is not None:
        try:
            old_conn.close()
        except Exception:  # noqa: BLE001
            pass
    return connect_postgres(db_url)


def call_with_db_retry(db_url: str, conn, write_fn):
    """Run ``write_fn(conn)``; on 08P01/26000, reconnect once and retry."""
    try:
        write_fn(conn)
        return conn
    except Exception as exc:  # noqa: BLE001
        if not is_prepare_bind_mismatch(exc):
            raise
        conn = reconnect_postgres(db_url, conn)
        try:
            write_fn(conn)
        except Exception as exc2:  # noqa: BLE001
            if is_prepare_bind_mismatch(exc2):
                raise PostgresConfigError(_BIND_MISMATCH_HINT) from exc2
            raise
        return conn
