"""G1 — gold_feature_coverage + missing top-N (no network)."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from spotify_pipeline.pipeline.gold import (
    FeatureCoverageReport,
    FeatureCoverageResult,
    GoldError,
    MissingFeatureRow,
    get_feature_coverage_report,
    query_feature_coverage,
    query_missing_features,
    sql_feature_coverage,
    sql_missing_features,
)
from spotify_pipeline.state.watermark import Watermark


def _wm() -> Watermark:
    return Watermark.parse("2026-11-12", "weekly_top_songs", "global")


def _settings() -> MagicMock:
    s = MagicMock()
    s.supabase_db_url = "postgresql://u:p@localhost/db"
    return s


def test_gold_queries_sql_file_has_sections_and_placeholders() -> None:
    from spotify_pipeline.pipeline.gold import _SQL_GOLD_QUERIES

    assert _SQL_GOLD_QUERIES.is_file()
    raw = _SQL_GOLD_QUERIES.read_text(encoding="utf-8")
    assert "-- @@query: feature_coverage" in raw
    assert "-- @@query: missing_features" in raw
    assert "/*__WHERE__*/" in raw
    assert "/*__BASE_JOIN__*/" in raw
    assert "/*__LIMIT__*/" in raw
    # missing_features composes Silver LEFT JOIN (do not paste BR-6 body there)
    missing = raw.split("-- @@query: missing_features", 1)[1].split("-- @@query:", 1)[0]
    assert "/*__BASE_JOIN__*/" in missing
    assert "FROM music.fact_chart AS f" not in missing


def test_sql_feature_coverage_loads_from_file() -> None:
    sql = sql_feature_coverage(_wm())
    assert "FROM music.gold_feature_coverage" in sql
    assert "/*__WHERE__*/" not in sql
    assert "2026-11-12" in sql
    assert "weekly_top_songs" in sql
    assert "global" in sql


def test_sql_missing_features_composes_silver_left_join() -> None:
    sql = sql_missing_features(_wm(), top_n=5)
    assert "LEFT JOIN music.dim_track" in sql
    assert "INNER JOIN" not in sql
    assert "features_found IS NOT TRUE" in sql
    assert "LIMIT 5" in sql
    assert "/*__BASE_JOIN__*/" not in sql
    assert "/*__LIMIT__*/" not in sql
    assert sql.count("WHERE f.chart_date") == 1
    # no comment-bleed orphan AND before inner SELECT
    inner = sql.split("FROM (", 1)[1].split(") AS j", 1)[0]
    preamble = inner.split("SELECT", 1)[0]
    assert "AND f.chart_type" not in preamble


def test_query_feature_coverage_maps_view_row() -> None:
    db = MagicMock()
    db.run.return_value = [
        (date(2026, 11, 12), "weekly_top_songs", "global", 50, 32, 64.0)
    ]

    with (
        patch("spotify_pipeline.pipeline.gold.readers.get_settings", return_value=_settings()),
        patch("spotify_pipeline.pipeline.gold.readers.require_db_url"),
        patch("spotify_pipeline.pipeline.gold.readers.connect_postgres", return_value=db),
    ):
        result = query_feature_coverage(_wm())

    assert result == FeatureCoverageResult(
        watermark=("2026-11-12", "weekly_top_songs", "global"),
        chart_rows=50,
        features_found_rows=32,
        features_found_pct=64.0,
    )
    sql = db.run.call_args[0][0]
    assert "FROM music.gold_feature_coverage" in sql
    assert "2026-11-12" in sql
    assert "weekly_top_songs" in sql
    assert "global" in sql
    db.close.assert_called_once()


def test_query_feature_coverage_empty_view_returns_none() -> None:
    db = MagicMock()
    db.run.return_value = []

    with (
        patch("spotify_pipeline.pipeline.gold.readers.get_settings", return_value=_settings()),
        patch("spotify_pipeline.pipeline.gold.readers.require_db_url"),
        patch("spotify_pipeline.pipeline.gold.readers.connect_postgres", return_value=db),
    ):
        assert query_feature_coverage(_wm()) is None


def test_query_missing_features_filters_not_true_and_limits() -> None:
    db = MagicMock()
    db.run.return_value = [
        (1, "t1", "Song A", False),
        (3, "t3", None, None),
    ]

    with (
        patch("spotify_pipeline.pipeline.gold.readers.get_settings", return_value=_settings()),
        patch("spotify_pipeline.pipeline.gold.readers.require_db_url"),
        patch("spotify_pipeline.pipeline.gold.readers.connect_postgres", return_value=db),
    ):
        rows = query_missing_features(_wm(), top_n=5)

    assert rows == [
        MissingFeatureRow(rank=1, track_id="t1", track_name="Song A", features_found=False),
        MissingFeatureRow(rank=3, track_id="t3", track_name=None, features_found=None),
    ]
    sql = db.run.call_args[0][0]
    assert "LEFT JOIN music.dim_track" in sql
    assert "INNER JOIN" not in sql
    assert "features_found IS NOT TRUE" in sql
    assert "LIMIT 5" in sql
    assert "2026-11-12" in sql


def test_query_missing_features_rejects_bad_top_n() -> None:
    with pytest.raises(GoldError, match="top_n"):
        query_missing_features(_wm(), top_n=0)


def test_get_feature_coverage_report_shared_conn() -> None:
    db = MagicMock()
    db.run.side_effect = [
        [(date(2026, 11, 12), "weekly_top_songs", "global", 50, 32, 64.0)],
        [(2, "miss", "No Features", False)],
    ]

    with (
        patch("spotify_pipeline.pipeline.gold.readers.get_settings", return_value=_settings()),
        patch("spotify_pipeline.pipeline.gold.readers.require_db_url"),
        patch("spotify_pipeline.pipeline.gold.readers.connect_postgres", return_value=db) as connect,
    ):
        report = get_feature_coverage_report(_wm(), missing_top_n=10)

    assert isinstance(report, FeatureCoverageReport)
    assert report.coverage is not None
    assert report.coverage.features_found_rows == 32
    assert len(report.missing) == 1
    assert report.missing[0].track_id == "miss"
    connect.assert_called_once()
    assert db.run.call_count == 2
    db.close.assert_called_once()


def test_get_feature_coverage_report_skips_missing_when_none() -> None:
    db = MagicMock()
    db.run.return_value = [
        (date(2026, 11, 12), "weekly_top_songs", "global", 50, 32, 64.0)
    ]

    with (
        patch("spotify_pipeline.pipeline.gold.readers.get_settings", return_value=_settings()),
        patch("spotify_pipeline.pipeline.gold.readers.require_db_url"),
        patch("spotify_pipeline.pipeline.gold.readers.connect_postgres", return_value=db),
    ):
        report = get_feature_coverage_report(_wm(), missing_top_n=None)

    assert report.coverage is not None
    assert report.missing == []
    assert db.run.call_count == 1
