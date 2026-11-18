"""Unit tests for C9 ingest_charts orchestration (mocked network/DB)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from spotify_pipeline.pipeline.ingest_charts import IngestChartsError, ingest_charts
from spotify_pipeline.state.watermark import Watermark


def _songs_payload(chart_date: str = "2026-11-12") -> dict:
    return {
        "chartEntryViewResponses": [
            {
                "displayChart": {
                    "date": chart_date,
                    "chartMetadata": {
                        "alias": "REGIONAL_GLOBAL_WEEKLY",
                        "dimensions": {"country": "GLOBAL", "latestDate": chart_date},
                    },
                },
                "entries": [
                    {
                        "chartEntryData": {
                            "currentRank": 1,
                            "previousRank": 2,
                        },
                        "trackMetadata": {"trackUri": "spotify:track:aaa111"},
                    }
                ],
            }
        ]
    }


def test_ingest_charts_writes_on_watermark_match() -> None:
    wm = Watermark.parse("2026-11-12", "weekly_top_songs", "global")
    fake_conn = MagicMock()
    settings = MagicMock()
    settings.supabase_db_url = "postgresql://u:p@localhost/db"
    settings.bronze_dir = None

    with (
        patch(
            "spotify_pipeline.pipeline.ingest_charts.fetch_public_charts",
            return_value=_songs_payload(),
        ),
        patch("spotify_pipeline.pipeline.ingest_charts.get_settings", return_value=settings),
        patch("spotify_pipeline.pipeline.ingest_charts.require_db_url"),
        patch(
            "spotify_pipeline.pipeline.ingest_charts.connect_postgres",
            return_value=fake_conn,
        ),
        patch(
            "spotify_pipeline.pipeline.ingest_charts.call_with_db_retry",
            side_effect=lambda db_url, conn, fn: (fn(conn), conn)[1],
        ),
        patch("spotify_pipeline.pipeline.ingest_charts.write_raw_charts") as write_raw,
        patch("spotify_pipeline.pipeline.ingest_charts.httpx.Client"),
    ):
        result = ingest_charts(wm, run_id="run123", write_fs=False)

    assert result["run_id"] == "run123"
    assert result["entry_count"] == 1
    assert result["watermark"] == ("2026-11-12", "weekly_top_songs", "global")
    write_raw.assert_called_once()
    kwargs = write_raw.call_args.kwargs
    assert kwargs["chart_date"] == "2026-11-12"
    assert kwargs["chart_type"] == "weekly_top_songs"
    fake_conn.close.assert_called_once()


def test_ingest_charts_rejects_watermark_mismatch() -> None:
    wm = Watermark.parse("2020-01-01", "weekly_top_songs", "global")
    settings = MagicMock()
    settings.supabase_db_url = "postgresql://u:p@localhost/db"
    settings.bronze_dir = None

    with (
        patch(
            "spotify_pipeline.pipeline.ingest_charts.fetch_public_charts",
            return_value=_songs_payload("2026-11-12"),
        ),
        patch("spotify_pipeline.pipeline.ingest_charts.get_settings", return_value=settings),
        patch("spotify_pipeline.pipeline.ingest_charts.require_db_url"),
        patch("spotify_pipeline.pipeline.ingest_charts.httpx.Client"),
        pytest.raises(IngestChartsError, match="mismatch"),
    ):
        ingest_charts(wm, write_fs=False)
