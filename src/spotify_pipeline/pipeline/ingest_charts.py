"""SPEC C9 — Charts → validate → Bronze (watermark-scoped)."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import httpx

from spotify_pipeline.clients.charts import (
    ALIAS_ALBUMS,
    ALIAS_ARTISTS,
    ALIAS_SONGS,
    ChartsError,
    chart_view_watermark,
    fetch_public_charts,
    view_by_alias,
)
from spotify_pipeline.config import get_settings
from spotify_pipeline.db.postgres import (
    call_with_db_retry,
    connect_postgres,
    require_db_url,
)
from spotify_pipeline.models.chart import ChartModelError, chart_entries_from_view
from spotify_pipeline.pipeline.bronze import write_raw_charts
from spotify_pipeline.state.watermark import Watermark, WatermarkError

_SOURCE = "charts_public_v0"

_CHART_TYPE_TO_ALIAS = {
    "weekly_top_songs": ALIAS_SONGS,
    "weekly_top_artists": ALIAS_ARTISTS,
    "weekly_top_albums": ALIAS_ALBUMS,
}


class IngestChartsError(RuntimeError):
    """Raised when C9 ingest-charts fails."""


def ingest_charts(
    watermark: Watermark,
    *,
    client: httpx.Client | None = None,
    run_id: str | None = None,
    bronze_dir: Path | None = None,
    write_fs: bool = True,
) -> dict[str, Any]:
    """Fetch Charts public/v0 for one watermark → validate → C8 write_raw_charts.

    Returns summary dict: run_id, watermark, entry_count, inserted.
    """
    alias = _CHART_TYPE_TO_ALIAS.get(watermark.chart_type)
    if alias is None:
        raise IngestChartsError(f"unsupported chart_type {watermark.chart_type!r}")

    settings = get_settings()
    require_db_url(settings)
    db_url = settings.supabase_db_url.strip()
    rid = run_id or uuid.uuid4().hex
    fs_dir = settings.bronze_dir if write_fs else None
    if bronze_dir is not None:
        fs_dir = bronze_dir

    owns = client is None
    http = client or httpx.Client(timeout=60.0)
    try:
        payload = fetch_public_charts(client=http)
        view = view_by_alias(payload, alias)
        live_date, live_type, live_country = chart_view_watermark(view)
        if not watermark.matches(live_date, live_type, live_country):
            raise IngestChartsError(
                "live chart watermark mismatch: "
                f"requested={watermark.as_tuple()} "
                f"live={(live_date, live_type, live_country)}. "
                "Use the live chart_date from Charts public/v0."
            )

        entries = chart_entries_from_view(view)
        row_payload = {
            "displayChart": view.get("displayChart"),
            "entries": view.get("entries") or [],
        }

        conn = connect_postgres(db_url)
        try:

            def _write(c: Any) -> None:
                write_raw_charts(
                    c,
                    run_id=rid,
                    source=_SOURCE,
                    chart_date=watermark.chart_date,
                    chart_type=watermark.chart_type,
                    country=watermark.country,
                    payload=row_payload,
                    bronze_dir=fs_dir,
                )

            call_with_db_retry(db_url, conn, _write)
        finally:
            conn.close()
    except (ChartsError, ChartModelError, WatermarkError) as exc:
        raise IngestChartsError(str(exc)) from exc
    finally:
        if owns:
            http.close()

    return {
        "run_id": rid,
        "watermark": watermark.as_tuple(),
        "entry_count": len(entries),
        "inserted": 1,
        "source": _SOURCE,
    }
