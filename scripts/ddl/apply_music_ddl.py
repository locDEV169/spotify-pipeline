#!/usr/bin/env python3
"""Migrate/apply SQL DDL to Supabase Postgres (schema music only).

Default file: docs/sql/music_schema.sql
Requires SUPABASE_DB_URL in .env (Dashboard → Database → Connect).
Uses pg8000 (pure Python). Never prints the connection string / password.

Usage:
    python scripts/ddl/apply_music_ddl.py
    python scripts/ddl/apply_music_ddl.py docs/sql/music_schema.sql
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"
_DEFAULT_SQL = _REPO_ROOT / "docs" / "sql" / "music_schema.sql"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

_FORBIDDEN = re.compile(
    r"\bweather_snapshots\b|\blifestyle_insights\b|\bcurrent_weather\b|"
    r"\bdrop\s+schema\s+public\b|\bdrop\s+table\s+public\.",
    re.IGNORECASE,
)


def _connect(db_url: str):
    import pg8000.native

    parsed = urlparse(db_url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise ValueError("SUPABASE_DB_URL must be a postgresql:// URI")
    user = unquote(parsed.username or "")
    password = unquote(parsed.password or "")
    host = parsed.hostname or ""
    port = parsed.port or 5432
    database = (parsed.path or "/postgres").lstrip("/") or "postgres"
    return pg8000.native.Connection(
        user=user,
        password=password,
        host=host,
        port=port,
        database=database,
        ssl_context=True,
    )


def _split_sql(sql: str) -> list[str]:
    """Split SQL file into statements; skip empty / comment-only chunks."""
    parts: list[str] = []
    buf: list[str] = []
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        buf.append(line)
        if stripped.endswith(";"):
            stmt = "\n".join(buf).strip().rstrip(";").strip()
            buf = []
            if stmt:
                parts.append(stmt)
    tail = "\n".join(buf).strip().rstrip(";").strip()
    if tail:
        parts.append(tail)
    return parts


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Apply music schema SQL to Supabase (never touches weather tables)."
    )
    p.add_argument(
        "sql_path",
        nargs="?",
        default=str(_DEFAULT_SQL),
        help=f"SQL file to apply (default: {_DEFAULT_SQL.as_posix()})",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        import pg8000.native  # noqa: F401
    except ModuleNotFoundError:
        print(
            'FAIL: thiếu pg8000. Chạy: python -m pip install -e ".[dev]"',
            file=sys.stderr,
        )
        return 2

    from spotify_pipeline.config import get_settings

    args = _parse_args(argv)
    sql_path = Path(args.sql_path)
    if not sql_path.is_file():
        print(f"FAIL: không thấy file SQL: {sql_path}", file=sys.stderr)
        return 2

    settings = get_settings()
    db_url = (settings.supabase_db_url or "").strip()
    if not db_url:
        print(
            "FAIL: chưa có SUPABASE_DB_URL trong .env.\n"
            "Lấy URI tại Supabase Dashboard → Project Settings → Database → Connect.\n"
            "Dán vào .env (không commit), rồi chạy lại:\n"
            "  python scripts/ddl/apply_music_ddl.py\n"
            "Hoặc paste docs/sql/music_schema.sql vào Dashboard → SQL Editor → Run.",
            file=sys.stderr,
        )
        return 2

    sql = sql_path.read_text(encoding="utf-8")
    if _FORBIDDEN.search(sql):
        print(
            "FAIL: SQL chứa tham chiếu weather / DROP public — abort.", file=sys.stderr
        )
        return 1
    if "CREATE SCHEMA IF NOT EXISTS music" not in sql:
        print("FAIL: SQL thiếu CREATE SCHEMA music — abort.", file=sys.stderr)
        return 1

    try:
        conn = _connect(db_url)
        try:
            statements = _split_sql(sql)
            for i, stmt in enumerate(statements, start=1):
                try:
                    conn.run(stmt)
                except Exception as exc:
                    preview = " ".join(stmt.split())[:120]
                    raise RuntimeError(
                        f"statement {i}/{len(statements)} failed near: {preview}"
                    ) from exc
            rows = conn.run(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'music'
                ORDER BY 1
                """
            )
            weather = conn.run(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN (
                    'weather_snapshots', 'lifestyle_insights', 'current_weather'
                  )
                ORDER BY 1
                """
            )
        finally:
            conn.close()
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    names = [r[0] for r in rows]
    print(f"OK migrate: file={sql_path.as_posix()} statements={len(statements)}")
    print(f"OK DDL applied: schema=music tables/views={len(names)}")
    print("OK music objects: " + ", ".join(names))
    wnames = [r[0] for r in weather]
    print("OK weather untouched: " + (", ".join(wnames) if wnames else "(none listed)"))
    print("Music SQL migrate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
