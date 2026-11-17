#!/usr/bin/env python3
"""Local smoke-check: Supabase create_client + Storage list_buckets.

Usage (from repo root, with `.env` filled):
    python scripts/check_supabase.py

Proves URL + service_role + network work. Does not require Silver/Gold tables.
Never prints SUPABASE_SERVICE_ROLE_KEY or DB passwords.
"""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import urlparse

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

try:
    import supabase  # noqa: F401
except ModuleNotFoundError:
    venv_python = _REPO_ROOT / ".venv" / "Scripts" / "python.exe"
    print(
        "FAIL: dependency `supabase` not found in this Python.\n"
        "Activate the project venv first, then retry:\n"
        "  source .venv/Scripts/activate   # Git Bash\n"
        '  python -m pip install -e ".[dev]"\n'
        f"Or run:  {venv_python} scripts/check_supabase.py",
        file=sys.stderr,
    )
    raise SystemExit(2) from None

from spotify_pipeline.config import get_settings
from spotify_pipeline.db.connection import (
    SupabaseConfigError,
    get_supabase_client,
)


def main() -> int:
    settings = get_settings()
    if (
        not settings.supabase_url.strip()
        or not settings.supabase_service_role_key.strip()
    ):
        print(
            "FAIL: set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env "
            "(see .env.example). Service role is server-only.",
            file=sys.stderr,
        )
        return 2

    host = urlparse(settings.supabase_url.strip()).netloc or "(unknown-host)"

    try:
        client = get_supabase_client(settings)
        buckets = client.storage.list_buckets()
        names = [
            getattr(b, "name", None) or (b.get("name") if isinstance(b, dict) else None)
            for b in buckets
        ]
        names = [n for n in names if n]
        print(f"OK supabase: host={host} buckets={len(buckets)}")
        if names:
            print(f"OK buckets: {', '.join(names)}")
    except SupabaseConfigError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print("Supabase smoke-check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
