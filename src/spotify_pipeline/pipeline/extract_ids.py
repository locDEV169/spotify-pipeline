"""Stage 4 EX — extract Spotify track/artist IDs from Bronze `raw_charts`.

Happy path: read latest `music.raw_charts` for the watermark (no live Charts).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from spotify_pipeline.clients.charts import spotify_id_from_uri
from spotify_pipeline.config import get_settings
from spotify_pipeline.db.postgres import (
    PostgresConfigError,
    connect_postgres,
    require_db_url,
)
from spotify_pipeline.models.chart import ChartModelError, chart_entries_from_view
from spotify_pipeline.state.watermark import Watermark


class ExtractIdsError(RuntimeError):
    """Raised when Bronze extract fails."""


@dataclass(frozen=True, slots=True)
class ExtractedIds:
    """IDs for one watermark, sourced from Bronze charts."""

    track_ids: list[str]
    artist_ids: list[str]
    watermark: tuple[str, str, str]
    raw_charts_id: int | None = None


def extract_ids(
    watermark: Watermark,
    *,
    conn: Any | None = None,
) -> ExtractedIds:
    """Load latest Bronze charts payload for watermark → track/artist IDs."""
    settings = get_settings()
    try:
        require_db_url(settings)
    except PostgresConfigError as exc:
        raise ExtractIdsError(str(exc)) from exc

    db_url = settings.supabase_db_url.strip()
    owns = conn is None
    db = conn or connect_postgres(db_url)
    try:
        raw_id, payload = fetch_latest_raw_charts_payload(db, watermark)
        return ids_from_bronze_payload(
            watermark, payload, raw_charts_id=raw_id
        )
    finally:
        if owns:
            db.close()


def fetch_latest_raw_charts_payload(
    conn: Any,
    watermark: Watermark,
) -> tuple[int | None, dict[str, Any]]:
    """Return (id, payload) for latest raw_charts row matching watermark."""
    sql = f"""
        SELECT id, payload
        FROM music.raw_charts
        WHERE chart_date = CAST({_sql_str(watermark.chart_date)} AS date)
          AND chart_type = {_sql_str(watermark.chart_type)}
          AND country = {_sql_str(watermark.country)}
        ORDER BY ingested_at DESC
        LIMIT 1
        """
    rows = conn.run(sql)
    if not rows:
        raise ExtractIdsError(
            "no Bronze raw_charts for watermark "
            f"{watermark.as_tuple()}; run ingest-charts first"
        )
    raw_id, payload = rows[0][0], rows[0][1]
    if isinstance(payload, str):
        payload = json.loads(payload)
    if not isinstance(payload, dict):
        raise ExtractIdsError("raw_charts.payload is not a JSON object")
    return (int(raw_id) if raw_id is not None else None, payload)


def ids_from_bronze_payload(
    watermark: Watermark,
    payload: dict[str, Any],
    *,
    raw_charts_id: int | None = None,
) -> ExtractedIds:
    """Parse IDs from ingest-shaped Bronze payload (displayChart + entries)."""
    if watermark.chart_type == "weekly_top_songs":
        try:
            entries = chart_entries_from_view(payload)
        except ChartModelError as exc:
            raise ExtractIdsError(str(exc)) from exc
        track_ids = list(dict.fromkeys(e.track_id for e in entries if e.track_id))
        if not track_ids:
            raise ExtractIdsError("Bronze charts has no track ids")
        return ExtractedIds(
            track_ids=track_ids,
            artist_ids=[],
            watermark=watermark.as_tuple(),
            raw_charts_id=raw_charts_id,
        )

    if watermark.chart_type == "weekly_top_artists":
        artist_ids = _artist_ids_from_entries(payload.get("entries") or [])
        if not artist_ids:
            raise ExtractIdsError("Bronze charts has no artist ids")
        return ExtractedIds(
            track_ids=[],
            artist_ids=artist_ids,
            watermark=watermark.as_tuple(),
            raw_charts_id=raw_charts_id,
        )

    raise ExtractIdsError(
        f"unsupported chart_type for extract: {watermark.chart_type!r}"
    )


def _artist_ids_from_entries(entries: Any) -> list[str]:
    if not isinstance(entries, list):
        return []
    ids: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        meta = entry.get("artistMetadata") or {}
        if not isinstance(meta, dict):
            continue
        aid = spotify_id_from_uri(str(meta.get("artistUri") or ""))
        if aid and aid not in ids:
            ids.append(aid)
    return ids


def _sql_str(value: str) -> str:
    return "'" + str(value).replace("'", "''") + "'"
