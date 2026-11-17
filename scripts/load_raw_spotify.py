#!/usr/bin/env python3
"""Fetch Spotify track JSON (Client Credentials) → INSERT music.raw_spotify.

Smoke Bronze loader — does not write Silver/Gold.

Usage:
    python scripts/load_raw_spotify.py
    python scripts/load_raw_spotify.py 003vvx7Niy0yvhvHt4a68B
    python scripts/load_raw_spotify.py <id1> <id2>

Prints run_id for later: python scripts/clear_raw_spotify.py --run-id <run_id>
Never prints secrets or access tokens.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# SPEC E2E / check_spotify probe
_DEFAULT_TRACK_ID = "003vvx7Niy0yvhvHt4a68B"
_SOURCE = "spotify_web_api"


def main() -> int:
    parser = argparse.ArgumentParser(description="Load Spotify tracks into music.raw_spotify")
    parser.add_argument(
        "track_ids",
        nargs="*",
        default=[_DEFAULT_TRACK_ID],
        help=f"Spotify track ids (default: {_DEFAULT_TRACK_ID})",
    )
    args = parser.parse_args()
    track_ids = list(dict.fromkeys(args.track_ids))  # dedupe, keep order

    try:
        import httpx
    except ModuleNotFoundError:
        print('FAIL: thiếu httpx. python -m pip install -e ".[dev]"', file=sys.stderr)
        return 2

    from spotify_pipeline.clients.spotify import SpotifyApiError, get_track
    from spotify_pipeline.clients.spotify_auth import SpotifyAuthError, get_access_token
    from spotify_pipeline.config import get_settings
    from spotify_pipeline.db.postgres import PostgresConfigError, connect_postgres, require_db_url

    settings = get_settings()
    if not settings.spotify_client_id or not settings.spotify_client_secret:
        print("FAIL: set SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET in .env", file=sys.stderr)
        return 2

    try:
        require_db_url(settings)
    except PostgresConfigError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2

    run_id = uuid.uuid4().hex
    inserted = 0

    try:
        with httpx.Client(timeout=30.0) as http:
            token = get_access_token(
                settings.spotify_client_id,
                settings.spotify_client_secret,
                client=http,
            )
            access = str(token["access_token"])

            conn = connect_postgres(settings.supabase_db_url.strip())
            try:
                for track_id in track_ids:
                    payload = get_track(access, track_id, client=http)
                    conn.run(
                        """
                        INSERT INTO music.raw_spotify
                            (run_id, source, entity, spotify_id, payload)
                        VALUES
                            (:run_id, :source, :entity, :spotify_id, CAST(:payload AS jsonb))
                        """,
                        run_id=run_id,
                        source=_SOURCE,
                        entity="track",
                        spotify_id=track_id,
                        payload=json.dumps(payload, ensure_ascii=False),
                    )
                    inserted += 1
                    name = payload.get("name", "?")
                    print(f"OK insert: spotify_id={track_id} name={name}")
            finally:
                conn.close()
    except (SpotifyAuthError, SpotifyApiError, PostgresConfigError, httpx.HTTPError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print(f"OK load_raw_spotify: inserted={inserted} run_id={run_id}")
    print(f"Clear later: python scripts/clear_raw_spotify.py --run-id {run_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
