"""SPEC C8 — Persist raw payloads + ingested_at.

Store of record: Postgres `music.raw_*` (jsonb; `ingested_at` = DEFAULT now()).
Optional dual-write: local filesystem under `bronze_dir` (Assumptions #4) with
envelope field `ingested_at` (ISO-8601 UTC).

C8 does not fetch APIs and does not open DB connections — callers pass `conn`.

DB writes use pg8000 *simple* queries (no bind params) so Supabase transaction
pooler :6543 does not break on unnamed prepared statements (08P01 / 26000).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
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
    bronze_dir: Path | None = None,
) -> None:
    """INSERT music.raw_charts; optionally mirror JSON under bronze_dir."""
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
    if bronze_dir is not None:
        day = chart_date or datetime.now(timezone.utc).date().isoformat()
        path = (
            Path(bronze_dir)
            / "charts"
            / "public_v0"
            / f"chart_date={day}"
            / f"{country}_{chart_type}.json"
        )
        _write_fs(
            path,
            {
                "ingested_at": _ingested_at(),
                "run_id": run_id,
                "source": source,
                "chart_date": chart_date,
                "chart_type": chart_type,
                "country": country,
                "payload": payload,
            },
        )


def write_raw_spotify(
    conn: Any,
    *,
    run_id: str,
    source: str,
    entity: str,
    spotify_id: str,
    payload: dict[str, Any],
    bronze_dir: Path | None = None,
) -> None:
    """INSERT music.raw_spotify; optionally mirror JSON under bronze_dir."""
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
    if bronze_dir is not None:
        day = datetime.now(timezone.utc).date().isoformat()
        folder = "tracks" if entity == "track" else "artists" if entity == "artist" else entity
        path = Path(bronze_dir) / "spotify" / folder / day / f"{spotify_id}.json"
        _write_fs(
            path,
            {
                "ingested_at": _ingested_at(),
                "run_id": run_id,
                "source": source,
                "entity": entity,
                "spotify_id": spotify_id,
                "payload": payload,
            },
        )


def write_raw_reccobeats(
    conn: Any,
    *,
    run_id: str,
    source: str,
    endpoint: str,
    spotify_track_ids: list[str],
    payload: dict[str, Any],
    bronze_dir: Path | None = None,
) -> None:
    """INSERT music.raw_reccobeats; optionally mirror JSON under bronze_dir."""
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
    if bronze_dir is not None:
        day = datetime.now(timezone.utc).date().isoformat()
        first = spotify_track_ids[0] if spotify_track_ids else "empty"
        path = (
            Path(bronze_dir)
            / "reccobeats"
            / endpoint
            / day
            / f"{run_id[:12]}_{len(spotify_track_ids)}_{first}.json"
        )
        _write_fs(
            path,
            {
                "ingested_at": _ingested_at(),
                "run_id": run_id,
                "source": source,
                "endpoint": endpoint,
                "spotify_track_ids": spotify_track_ids,
                "payload": payload,
            },
        )


def _ingested_at() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_fs(path: Path, envelope: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


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
