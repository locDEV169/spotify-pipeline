#!/usr/bin/env python3
"""Fetch Charts public/v0 → INSERT music.raw_charts (Bronze).

Default: store Weekly Top Songs: Global + Weekly Top Artists: Global views
(one row per chart watermark). Does not write Silver/Gold.

Usage:
    python scripts/bronze/load_raw_charts.py
    python scripts/bronze/load_raw_charts.py --songs-only
    python scripts/bronze/load_raw_charts.py --artists-only

Prints run_id for: python scripts/bronze/clear_raw_charts.py --run-id <run_id>
Never prints secrets.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

_SOURCE = "charts_public_v0"


def main() -> int:
    parser = argparse.ArgumentParser(description="Load Charts public/v0 into music.raw_charts")
    parser.add_argument("--songs-only", action="store_true", help="Only Weekly Top Songs: Global")
    parser.add_argument("--artists-only", action="store_true", help="Only Weekly Top Artists: Global")
    args = parser.parse_args()
    if args.songs_only and args.artists_only:
        print("FAIL: use only one of --songs-only / --artists-only", file=sys.stderr)
        return 2

    try:
        import httpx
    except ModuleNotFoundError:
        print('FAIL: thiếu httpx. python -m pip install -e ".[dev]"', file=sys.stderr)
        return 2

    from spotify_pipeline.clients.charts import (
        ALIAS_ARTISTS,
        ALIAS_SONGS,
        ChartsError,
        chart_view_watermark,
        fetch_public_charts,
        view_by_alias,
    )
    from spotify_pipeline.config import get_settings
    from spotify_pipeline.db.postgres import (
        PostgresConfigError,
        connect_postgres,
        require_db_url,
    )
    from spotify_pipeline.pipeline.bronze import write_raw_charts

    settings = get_settings()
    try:
        require_db_url(settings)
    except PostgresConfigError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2

    aliases: list[str] = []
    if args.artists_only:
        aliases = [ALIAS_ARTISTS]
    elif args.songs_only:
        aliases = [ALIAS_SONGS]
    else:
        aliases = [ALIAS_SONGS, ALIAS_ARTISTS]

    run_id = uuid.uuid4().hex
    inserted = 0

    try:
        with httpx.Client(timeout=60.0) as http:
            payload = fetch_public_charts(client=http)
            conn = connect_postgres(settings.supabase_db_url.strip())
            try:
                for alias in aliases:
                    view = view_by_alias(payload, alias)
                    chart_date, chart_type, country = chart_view_watermark(view)
                    entries = view.get("entries") or []
                    # Store the chart view (display + entries), not unrelated sibling charts.
                    row_payload = {
                        "displayChart": view.get("displayChart"),
                        "entries": entries,
                    }
                    write_raw_charts(
                        conn,
                        run_id=run_id,
                        source=_SOURCE,
                        chart_date=chart_date,
                        chart_type=chart_type,
                        country=country,
                        payload=row_payload,
                    )
                    inserted += 1
                    print(
                        f"OK insert: alias={alias} chart_date={chart_date} "
                        f"chart_type={chart_type} country={country} entries={len(entries)}"
                    )
            finally:
                conn.close()
    except (ChartsError, PostgresConfigError, httpx.HTTPError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print(f"OK load_raw_charts: inserted={inserted} run_id={run_id}")
    print(f"Clear later: python scripts/bronze/clear_raw_charts.py --run-id {run_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
