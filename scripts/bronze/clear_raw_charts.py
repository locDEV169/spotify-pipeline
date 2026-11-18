#!/usr/bin/env python3
"""Delete rows from music.raw_charts only (never weather / other music tables).

Usage:
    python scripts/bronze/clear_raw_charts.py --run-id <run_id>
    python scripts/bronze/clear_raw_charts.py --all --yes
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def main() -> int:
    parser = argparse.ArgumentParser(description="Clear rows from music.raw_charts")
    parser.add_argument("--run-id", help="Delete rows with this run_id")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Delete ALL rows in music.raw_charts (requires --yes)",
    )
    parser.add_argument("--yes", action="store_true", help="Confirm dangerous --all delete")
    args = parser.parse_args()

    if args.all:
        if not args.yes:
            print("FAIL: --all requires --yes", file=sys.stderr)
            return 2
        mode = "all"
    elif args.run_id:
        mode = "run_id"
    else:
        print(
            "FAIL: pass --run-id <id> (or --all --yes to wipe music.raw_charts).",
            file=sys.stderr,
        )
        return 2

    from spotify_pipeline.config import get_settings
    from spotify_pipeline.db.postgres import (
        PostgresConfigError,
        connect_postgres,
        require_db_url,
    )

    settings = get_settings()
    try:
        require_db_url(settings)
    except PostgresConfigError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2

    try:
        conn = connect_postgres(settings.supabase_db_url.strip())
        try:
            if mode == "all":
                rows = conn.run("DELETE FROM music.raw_charts RETURNING id")
            else:
                rows = conn.run(
                    "DELETE FROM music.raw_charts WHERE run_id = :run_id RETURNING id",
                    run_id=args.run_id,
                )
            deleted = len(rows)
        finally:
            conn.close()
    except Exception as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print(f"OK clear_raw_charts: mode={mode} deleted={deleted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
