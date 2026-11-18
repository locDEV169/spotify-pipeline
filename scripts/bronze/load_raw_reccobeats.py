#!/usr/bin/env python3
"""Fetch ReccoBeats audio-features → INSERT music.raw_reccobeats (Bronze).

Default (no ids): Charts public/v0 Weekly Global Top Songs track ids (~50),
chunked ≤40. Optional: pass explicit Spotify track ids.

Usage:
    python scripts/bronze/load_raw_reccobeats.py
    python scripts/bronze/load_raw_reccobeats.py 003vvx7Niy0yvhvHt4a68B
    python scripts/bronze/load_raw_reccobeats.py <id1> <id2>

Prints run_id for: python scripts/bronze/clear_raw_reccobeats.py --run-id <run_id>
Never prints secrets.
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

_SOURCE = "reccobeats"
_ENDPOINT = "audio-features"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Load ReccoBeats audio-features into music.raw_reccobeats"
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
        help="Max track ids from Charts (default: all ≈50)",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.05,
        help="Seconds between ReccoBeats batches (default: 0.05)",
    )
    args = parser.parse_args()

    try:
        import httpx
    except ModuleNotFoundError:
        print('FAIL: thiếu httpx. python -m pip install -e ".[dev]"', file=sys.stderr)
        return 2

    from spotify_pipeline.clients.charts import (
        ChartsError,
        fetch_public_charts,
        weekly_global_top_song_track_ids,
    )
    from spotify_pipeline.clients.reccobeats import (
        ReccoBeatsError,
        audio_features_hits_misses,
        chunk_ids,
        get_audio_features,
    )
    from spotify_pipeline.config import get_settings
    from spotify_pipeline.db.postgres import (
        PostgresConfigError,
        call_with_db_retry,
        connect_postgres,
        require_db_url,
    )
    from spotify_pipeline.pipeline.bronze import write_raw_reccobeats

    settings = get_settings()
    batch_size = settings.reccobeats_batch_size or 40

    try:
        require_db_url(settings)
    except PostgresConfigError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2

    explicit = list(dict.fromkeys(args.track_ids))
    run_id = uuid.uuid4().hex
    inserted = 0

    try:
        with httpx.Client(timeout=60.0) as http:
            if explicit:
                track_ids = explicit
                print(f"OK mode=explicit_tracks count={len(track_ids)}")
            else:
                charts = fetch_public_charts(client=http)
                track_ids = weekly_global_top_song_track_ids(charts, limit=args.limit)
                print(f"OK charts songs: {len(track_ids)} track ids")

            if not track_ids:
                print("FAIL: no track ids to load", file=sys.stderr)
                return 2

            batches = chunk_ids(track_ids, size=batch_size)
            print(f"OK batches={len(batches)} batch_size={batch_size}")

            db_url = settings.supabase_db_url.strip()
            conn = connect_postgres(db_url)
            try:
                for i, batch in enumerate(batches, start=1):
                    payload = get_audio_features(batch, client=http)
                    hits, misses = audio_features_hits_misses(batch, payload)

                    def _write(c, _batch=batch, _payload=payload):
                        write_raw_reccobeats(
                            c,
                            run_id=run_id,
                            source=_SOURCE,
                            endpoint=_ENDPOINT,
                            spotify_track_ids=_batch,
                            payload=_payload,
                        )

                    conn = call_with_db_retry(db_url, conn, _write)
                    inserted += 1
                    print(
                        f"OK batch {i}/{len(batches)}: "
                        f"requested={len(batch)} hits={len(hits)} misses={len(misses)}"
                    )
                    if args.sleep and i < len(batches):
                        time.sleep(args.sleep)
            finally:
                conn.close()
    except (
        ChartsError,
        ReccoBeatsError,
        PostgresConfigError,
        httpx.HTTPError,
    ) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print(f"OK load_raw_reccobeats: inserted={inserted} run_id={run_id}")
    print(
        f"Clear later: python scripts/bronze/clear_raw_reccobeats.py --run-id {run_id}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
