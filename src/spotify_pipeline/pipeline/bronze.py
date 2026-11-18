"""SPEC C8 — Persist raw payloads + ingested_at.

Store of record (project choice): Postgres `music.raw_*` (jsonb).
Local filesystem `data/bronze/` (Assumptions #4) is deferred.

C8 does not fetch APIs and does not open DB connections — callers pass `conn`.
`ingested_at` comes from table DEFAULT now().

Writes use pg8000 *simple* queries (no bind params) so Supabase transaction
pooler :6543 does not break on unnamed prepared statements (08P01 / 26000).
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
    date_sql = "NULL" if chart_date is None else f"CAST({_sql_str(chart_date)} AS date)"
    sql = f"""
        INSERT INTO music.raw_charts
            (run_id, source, chart_date, chart_type, country, payload)
        VALUES
            (
              {_sql_str(run_id)},
              {_sql_str(source)},
              {date_sql},
              {_sql_str(chart_type)},
              {_sql_str(country)},
              {_sql_jsonb(payload)}
            )
        """
    conn.run(sql)


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
    sql = f"""
        INSERT INTO music.raw_spotify
            (run_id, source, entity, spotify_id, payload)
        VALUES
            (
              {_sql_str(run_id)},
              {_sql_str(source)},
              {_sql_str(entity)},
              {_sql_str(spotify_id)},
              {_sql_jsonb(payload)}
            )
        """
    conn.run(sql)


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
    sql = f"""
        INSERT INTO music.raw_reccobeats
            (run_id, source, endpoint, spotify_track_ids, payload)
        VALUES
            (
              {_sql_str(run_id)},
              {_sql_str(source)},
              {_sql_str(endpoint)},
              {_sql_text_array(spotify_track_ids)},
              {_sql_jsonb(payload)}
            )
        """
    conn.run(sql)


def _sql_str(value: str) -> str:
    """Single-quoted SQL string literal."""
    return "'" + str(value).replace("'", "''") + "'"


def _sql_jsonb(payload: dict[str, Any]) -> str:
    """Dollar-quoted JSON cast to jsonb (avoids quote escaping)."""
    raw = json.dumps(payload, ensure_ascii=False)
    tag = "j"
    while f"${tag}$" in raw:
        tag += "x"
    return f"${tag}${raw}${tag}$::jsonb"


def _sql_text_array(values: list[str]) -> str:
    """ARRAY['a','b']::text[] literal."""
    inner = ", ".join(_sql_str(v) for v in values)
    return f"ARRAY[{inner}]::text[]"
