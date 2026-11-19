"""G5/G6 — build_gold one-pass + SCD2 deferred (no network)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from spotify_pipeline.pipeline.gold import SCD2_STATUS, build_gold
from spotify_pipeline.pipeline.gold.readers import (
    FeatureCoverageReport,
    FeatureCoverageResult,
    MoodRow,
    MoverRow,
    PopularityFeatureResult,
)
from spotify_pipeline.state.watermark import Watermark


def _wm() -> Watermark:
    return Watermark.parse("2026-11-12", "weekly_top_songs", "global")


def _settings() -> MagicMock:
    s = MagicMock()
    s.supabase_db_url = "postgresql://u:p@localhost/db"
    return s


def test_scd2_deferred_constant() -> None:
    assert SCD2_STATUS == "deferred"


def test_build_gold_one_pass_orchestrates_readers() -> None:
    db = MagicMock()
    coverage = FeatureCoverageResult(
        watermark=("2026-11-12", "weekly_top_songs", "global"),
        chart_rows=50,
        features_found_rows=32,
        features_found_pct=64.0,
    )
    report = FeatureCoverageReport(coverage=coverage, missing=[MagicMock()] * 3)
    movers = [
        MoverRow(
            track_id="t1",
            track_name="A",
            rank=1,
            prev_rank=2,
            rank_delta=1,
            streams=None,
        )
    ]
    mood = [
        MoodRow(
            track_id="t1",
            track_name="A",
            energy=0.8,
            valence=0.7,
            tempo=120.0,
            source_features="reccobeats",
            mood="energetic",
        )
    ]
    popularity = PopularityFeatureResult(
        rows=[], skipped=True, reason="no_non_null_track_popularity_or_features"
    )

    with (
        patch(
            "spotify_pipeline.pipeline.gold.build.get_settings",
            return_value=_settings(),
        ),
        patch("spotify_pipeline.pipeline.gold.build.require_db_url"),
        patch(
            "spotify_pipeline.pipeline.gold.build.connect_postgres",
            return_value=db,
        ) as connect,
        patch(
            "spotify_pipeline.pipeline.gold.build.get_feature_coverage_report",
            return_value=report,
        ) as cov,
        patch(
            "spotify_pipeline.pipeline.gold.build.query_movers",
            return_value=movers,
        ) as mov,
        patch(
            "spotify_pipeline.pipeline.gold.build.query_mood_segments",
            return_value=mood,
        ) as md,
        patch(
            "spotify_pipeline.pipeline.gold.build.query_popularity_feature_pairs",
            return_value=popularity,
        ) as pop,
    ):
        result = build_gold(_wm())

    connect.assert_called_once()
    cov.assert_called_once()
    mov.assert_called_once()
    md.assert_called_once()
    pop.assert_called_once()
    assert result.watermark == ("2026-11-12", "weekly_top_songs", "global")
    assert result.coverage is not None
    assert result.coverage.features_found_pct == 64.0
    assert result.missing_count == 3
    assert result.movers_count == 1
    assert result.mood_count == 1
    assert result.popularity_skipped is True
    assert result.popularity_pairs == 0
    assert result.scd2_status == "deferred"
    db.close.assert_called_once()
