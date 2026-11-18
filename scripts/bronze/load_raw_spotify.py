#!/usr/bin/env python3
"""Fetch Spotify track/artist JSON → INSERT music.raw_spotify.

Default (no ids): Charts public/v0 Weekly Global Top Songs (50) + Top Artists (50).
Optional: pass explicit track ids (legacy Brightside-style smoke).

Usage:
    python scripts/bronze/load_raw_spotify.py
    python scripts/bronze/load_raw_spotify.py 003vvx7Niy0yvhvHt4a68B
    python scripts/bronze/load_raw_spotify.py <id1> <id2>

Prints run_id for later: python scripts/bronze/clear_raw_spotify.py --run-id <run_id>
Never prints secrets or access tokens.
"""

from __future__ import annotations

import argparse
import sys
import time
import uuid
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

_SOURCE = "spotify_web_api"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Load Spotify tracks/artists into music.raw_spotify"
    )
    parser.add_argument(
        "track_ids",
        nargs="*",
        help="Optional explicit Spotify track ids (skips Charts when provided)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max songs and/or artists from Charts (default: all ≈50 each)",
    )
    parser.add_argument(
        "--tracks-only",
        action="store_true",
        help="Only load Global Top Songs tracks",
    )
    parser.add_argument(
        "--artists-only",
        action="store_true",
        help="Only load Global Top Artists",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.05,
        help="Seconds between Web API calls (default: 0.05)",
    )
    args = parser.parse_args()
    if args.tracks_only and args.artists_only:
        print("FAIL: use only one of --tracks-only / --artists-only", file=sys.stderr)
        return 2

    try:
        import httpx
    except ModuleNotFoundError:
        print('FAIL: thiếu httpx. python -m pip install -e ".[dev]"', file=sys.stderr)
        return 2

    from spotify_pipeline.clients.charts import (
        ChartsError,
        fetch_public_charts,
        weekly_global_top_artist_ids,
        weekly_global_top_song_track_ids,
    )
    from spotify_pipeline.clients.spotify import SpotifyApiError, get_artist, get_track
    from spotify_pipeline.clients.spotify_auth import SpotifyAuthError, get_access_token
    from spotify_pipeline.config import get_settings
    from spotify_pipeline.db.postgres import (
        PostgresConfigError,
        call_with_db_retry,
        connect_postgres,
        require_db_url,
    )
    from spotify_pipeline.pipeline.bronze import write_raw_spotify

    settings = get_settings()
    if not settings.spotify_client_id or not settings.spotify_client_secret:
        print(
            "FAIL: set SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET in .env",
            file=sys.stderr,
        )
        return 2

    try:
        require_db_url(settings)
    except PostgresConfigError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2

    explicit_tracks = list(dict.fromkeys(args.track_ids))
    track_ids: list[str] = []
    artist_ids: list[str] = []

    run_id = uuid.uuid4().hex
    inserted = 0

    try:
        with httpx.Client(timeout=60.0) as http:
            if explicit_tracks:
                track_ids = explicit_tracks
                print(f"OK mode=explicit_tracks count={len(track_ids)}")
            else:
                charts = fetch_public_charts(client=http)
                if not args.artists_only:
                    track_ids = weekly_global_top_song_track_ids(
                        charts, limit=args.limit
                    )
                    print(f"OK charts songs: {len(track_ids)} track ids")
                if not args.tracks_only:
                    artist_ids = weekly_global_top_artist_ids(charts, limit=args.limit)
                    print(f"OK charts artists: {len(artist_ids)} artist ids")

            token = get_access_token(
                settings.spotify_client_id,
                settings.spotify_client_secret,
                client=http,
            )
            access = str(token["access_token"])

            db_url = settings.supabase_db_url.strip()
            conn = connect_postgres(db_url)
            try:
                for track_id in track_ids:
                    payload = get_track(access, track_id, client=http)

                    def _write_track(c, _payload=payload, _id=track_id):
                        write_raw_spotify(
                            c,
                            run_id=run_id,
                            source=_SOURCE,
                            entity="track",
                            spotify_id=_id,
                            payload=_payload,
                            bronze_dir=settings.bronze_dir,
                        )

                    conn = call_with_db_retry(db_url, conn, _write_track)
                    inserted += 1
                    print(f"OK track: {track_id} | {payload.get('name', '?')}")
                    if args.sleep:
                        time.sleep(args.sleep)

                for artist_id in artist_ids:
                    payload = get_artist(access, artist_id, client=http)

                    def _write_artist(c, _payload=payload, _id=artist_id):
                        write_raw_spotify(
                            c,
                            run_id=run_id,
                            source=_SOURCE,
                            entity="artist",
                            spotify_id=_id,
                            payload=_payload,
                            bronze_dir=settings.bronze_dir,
                        )

                    conn = call_with_db_retry(db_url, conn, _write_artist)
                    inserted += 1
                    print(f"OK artist: {artist_id} | {payload.get('name', '?')}")
                    if args.sleep:
                        time.sleep(args.sleep)
            finally:
                conn.close()
    except (
        ChartsError,
        SpotifyAuthError,
        SpotifyApiError,
        PostgresConfigError,
        httpx.HTTPError,
    ) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print(f"OK load_raw_spotify: inserted={inserted} run_id={run_id}")
    print(f"Clear later: python scripts/bronze/clear_raw_spotify.py --run-id {run_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
