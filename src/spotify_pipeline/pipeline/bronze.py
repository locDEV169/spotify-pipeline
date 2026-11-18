"""SPEC C8 — Persist raw payloads + ingested_at.

Store of record (project choice): Postgres `music.raw_*` (jsonb).
Local filesystem `data/bronze/` (Assumptions #4) is deferred.

C8 does not fetch APIs and does not open DB connections — callers pass `conn`.
`ingested_at` comes from table DEFAULT now().
"""

from __future__ import annotations

import json
from typing import Any


def write_raw_charts(
    conn: Any,
    *,
    run_id: str,
    source: str,
    chart_date: str | None,
    chart_type: str,
    country: str,
    payload: dict[str, Any],
) -> None:
    """INSERT one row into music.raw_charts."""
    conn.run(
        """
        INSERT INTO music.raw_charts
            (run_id, source, chart_date, chart_type, country, payload)
        VALUES
            (
              :run_id, :source, CAST(:chart_date AS date),
              :chart_type, :country, CAST(:payload AS jsonb)
            )
        """,
        run_id=run_id,
        source=source,
        chart_date=chart_date,
        chart_type=chart_type,
        country=country,
        payload=json.dumps(payload, ensure_ascii=False),
    )


def write_raw_spotify(
    conn: Any,
    *,
    run_id: str,
    source: str,
    entity: str,
    spotify_id: str,
    payload: dict[str, Any],
) -> None:
    """INSERT one row into music.raw_spotify."""
    conn.run(
        """
        INSERT INTO music.raw_spotify
            (run_id, source, entity, spotify_id, payload)
        VALUES
            (:run_id, :source, :entity, :spotify_id, CAST(:payload AS jsonb))
        """,
        run_id=run_id,
        source=source,
        entity=entity,
        spotify_id=spotify_id,
        payload=json.dumps(payload, ensure_ascii=False),
    )


def write_raw_reccobeats(
    conn: Any,
    *,
    run_id: str,
    source: str,
    endpoint: str,
    spotify_track_ids: list[str],
    payload: dict[str, Any],
) -> None:
    """INSERT one row into music.raw_reccobeats (one API batch)."""
    conn.run(
        """
        INSERT INTO music.raw_reccobeats
            (run_id, source, endpoint, spotify_track_ids, payload)
        VALUES
            (
              :run_id,
              :source,
              :endpoint,
              :spotify_track_ids,
              CAST(:payload AS jsonb)
            )
        """,
        run_id=run_id,
        source=source,
        endpoint=endpoint,
        spotify_track_ids=spotify_track_ids,
        payload=json.dumps(payload, ensure_ascii=False),
    )
