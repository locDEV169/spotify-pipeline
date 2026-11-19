"""G4 — popularity vs features null-safe skip (no network)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from spotify_pipeline.pipeline.gold import (
    PopularityFeaturePair,
    PopularityFeatureResult,
    query_popularity_feature_pairs,
    sql_popularity_feature_pairs,
)
from spotify_pipeline.state.watermark import Watermark


def _wm() -> Watermark:
    return Watermark.parse("2026-11-12", "weekly_top_songs", "global")


def _settings() -> MagicMock:
    s = MagicMock()
    s.supabase_db_url = "postgresql://u:p@localhost/db"
    return s


def test_gold_queries_sql_has_popularity_section() -> None:
    from spotify_pipeline.pipeline.gold import _SQL_GOLD_QUERIES

    assert _SQL_GOLD_QUERIES.is_file()
    raw = _SQL_GOLD_QUERIES.read_text(encoding="utf-8")
    assert "-- @@query: popularity_feature_pairs" in raw
    assert "track_popularity" in raw
    assert "LEFT JOIN music.dim_track" in raw
    assert "/*__WHERE__*/" in raw


def test_sql_popularity_feature_pairs_injects_f_alias_watermark() -> None:
    sql = sql_popularity_feature_pairs(_wm())
    assert "f.chart_date" in sql
    assert "f.chart_type" in sql
    assert "f.country" in sql
    assert "/*__WHERE__*/" not in sql
    assert "2026-11-12" in sql
    assert "track_popularity IS NOT NULL" in sql


def test_query_popularity_all_null_skips() -> None:
    db = MagicMock()
    db.run.return_value = []

    with (
        patch(
            "spotify_pipeline.pipeline.gold.readers.get_settings",
            return_value=_settings(),
        ),
        patch("spotify_pipeline.pipeline.gold.readers.require_db_url"),
        patch(
            "spotify_pipeline.pipeline.gold.readers.connect_postgres",
            return_value=db,
        ),
    ):
        result = query_popularity_feature_pairs(_wm())

    assert isinstance(result, PopularityFeatureResult)
    assert result.skipped is True
    assert result.rows == []
    assert result.reason == "no_non_null_track_popularity_or_features"
    db.close.assert_called_once()


def test_query_popularity_mixed_returns_only_non_null() -> None:
    db = MagicMock()
    db.run.return_value = [
        (1, "t1", "Has Pop", 72, 0.8, 0.6, 0.7),
        (3, "t3", None, 40, None, 0.2, None),
    ]

    with (
        patch(
            "spotify_pipeline.pipeline.gold.readers.get_settings",
            return_value=_settings(),
        ),
        patch("spotify_pipeline.pipeline.gold.readers.require_db_url"),
        patch(
            "spotify_pipeline.pipeline.gold.readers.connect_postgres",
            return_value=db,
        ),
    ):
        result = query_popularity_feature_pairs(_wm())

    assert result.skipped is False
    assert result.reason is None
    assert result.rows == [
        PopularityFeaturePair(
            rank=1,
            track_id="t1",
            track_name="Has Pop",
            track_popularity=72,
            energy=0.8,
            valence=0.6,
            danceability=0.7,
        ),
        PopularityFeaturePair(
            rank=3,
            track_id="t3",
            track_name=None,
            track_popularity=40,
            energy=None,
            valence=0.2,
            danceability=None,
        ),
    ]
    # never invent: every row has real popularity
    assert all(r.track_popularity is not None for r in result.rows)
