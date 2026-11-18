"""Unit tests for Silver W1 fact_chart (Bronze → upsert; no network)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from spotify_pipeline.models.chart import ChartEntry
from spotify_pipeline.pipeline.silver import (
    SilverError,
    build_fact_chart,
    fact_entries_from_bronze_payload,
    upsert_fact_chart_rows,
)
from spotify_pipeline.state.watermark import Watermark


def _songs_bronze_payload() -> dict:
    return {
        "displayChart": {"date": "2026-11-12"},
        "entries": [
            {
                "chartEntryData": {
                    "currentRank": 1,
                    "previousRank": 2,
                    "entryStatus": "MOVED_UP",
                },
                "trackMetadata": {"trackUri": "spotify:track:aaa111"},
            },
            {
                "chartEntryData": {"currentRank": 2},
                "trackMetadata": {"trackUri": "spotify:track:bbb222"},
            },
        ],
    }


def test_fact_entries_from_bronze_payload() -> None:
    rows = fact_entries_from_bronze_payload(_songs_bronze_payload())
    assert len(rows) == 2
    assert rows[0].track_id == "aaa111"
    assert rows[0].rank == 1
    assert rows[0].prev_rank == 2
    assert rows[0].streams is None
    assert rows[0].entry_status == "MOVED_UP"
    assert rows[1].track_id == "bbb222"
    assert rows[1].entry_status is None


def test_upsert_fact_chart_rows_sql_shape() -> None:
    wm = Watermark.parse("2026-11-12", "weekly_top_songs", "global")
    entries = [
        ChartEntry(
            track_id="aaa111",
            rank=1,
            prev_rank=2,
            streams=None,
            entry_status="MOVED_UP",
        )
    ]
    conn = MagicMock()
    n = upsert_fact_chart_rows(conn, wm, entries, run_id="rid1")
    assert n == 1
    sql = conn.run.call_args.args[0]
    assert "INSERT INTO music.fact_chart" in sql
    assert "ON CONFLICT (chart_date, chart_type, country, track_id)" in sql
    assert "2026-11-12" in sql
    assert "aaa111" in sql
    assert "MOVED_UP" in sql
    assert "NULL" in sql  # streams


def test_upsert_fact_chart_rows_rejects_empty() -> None:
    wm = Watermark.parse("2026-11-12", "weekly_top_songs", "global")
    with pytest.raises(SilverError, match="no ChartEntry"):
        upsert_fact_chart_rows(MagicMock(), wm, [], run_id="rid1")


def test_build_fact_chart_from_bronze() -> None:
    wm = Watermark.parse("2026-11-12", "weekly_top_songs", "global")
    fake_conn = MagicMock()
    fake_conn.run.side_effect = [
        [(42, _songs_bronze_payload())],  # SELECT latest raw_charts
        None,  # INSERT row 1
        None,  # INSERT row 2
    ]
    settings = MagicMock()
    settings.supabase_db_url = "postgresql://u:p@localhost/db"

    with (
        patch("spotify_pipeline.pipeline.silver.get_settings", return_value=settings),
        patch("spotify_pipeline.pipeline.silver.require_db_url"),
        patch(
            "spotify_pipeline.pipeline.silver.connect_postgres",
            return_value=fake_conn,
        ),
    ):
        result = build_fact_chart(wm, run_id="fixed-run")

    assert result.upserted == 2
    assert result.raw_charts_id == 42
    assert result.run_id == "fixed-run"
    assert result.watermark == ("2026-11-12", "weekly_top_songs", "global")
    fake_conn.close.assert_called_once()
    assert fake_conn.run.call_count == 3
    select_sql = fake_conn.run.call_args_list[0].args[0]
    assert "music.raw_charts" in select_sql
    insert_sql = fake_conn.run.call_args_list[1].args[0]
    assert "music.fact_chart" in insert_sql


def test_build_fact_chart_idempotent_second_pass() -> None:
    """Re-run issues same upsert statements (ON CONFLICT), no extra tables."""
    wm = Watermark.parse("2026-11-12", "weekly_top_songs", "global")
    fake_conn = MagicMock()
    fake_conn.run.side_effect = [
        [(7, _songs_bronze_payload())],
        None,
        None,
        [(7, _songs_bronze_payload())],
        None,
        None,
    ]
    settings = MagicMock()
    settings.supabase_db_url = "postgresql://u:p@localhost/db"

    with (
        patch("spotify_pipeline.pipeline.silver.get_settings", return_value=settings),
        patch("spotify_pipeline.pipeline.silver.require_db_url"),
        patch(
            "spotify_pipeline.pipeline.silver.connect_postgres",
            return_value=fake_conn,
        ),
    ):
        a = build_fact_chart(wm, run_id="r1")
        b = build_fact_chart(wm, run_id="r2")

    assert a.upserted == b.upserted == 2
    insert_calls = [
        c.args[0]
        for c in fake_conn.run.call_args_list
        if "INSERT INTO music.fact_chart" in c.args[0]
    ]
    assert len(insert_calls) == 4
    assert all("ON CONFLICT" in sql for sql in insert_calls)
    assert all("dim_" not in sql for sql in insert_calls)


def test_build_fact_chart_missing_bronze() -> None:
    wm = Watermark.parse("2026-11-12", "weekly_top_songs", "global")
    fake_conn = MagicMock()
    fake_conn.run.return_value = []
    settings = MagicMock()
    settings.supabase_db_url = "postgresql://u:p@localhost/db"

    with (
        patch("spotify_pipeline.pipeline.silver.get_settings", return_value=settings),
        patch("spotify_pipeline.pipeline.silver.require_db_url"),
        patch(
            "spotify_pipeline.pipeline.silver.connect_postgres",
            return_value=fake_conn,
        ),
        pytest.raises(SilverError, match="no Bronze raw_charts"),
    ):
        build_fact_chart(wm)


def test_build_fact_chart_rejects_artists_chart() -> None:
    wm = Watermark.parse("2026-11-12", "weekly_top_artists", "global")
    with pytest.raises(SilverError, match="unsupported chart_type"):
        build_fact_chart(wm)
