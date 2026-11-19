"""G3 — gold_mood_segments + energy×valence labels (no network)."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

from spotify_pipeline.pipeline.gold import MoodRow, query_mood_segments, sql_mood_segments
from spotify_pipeline.pipeline.gold.readers import _mood_label
from spotify_pipeline.state.watermark import Watermark


def _wm() -> Watermark:
    return Watermark.parse("2026-11-12", "weekly_top_songs", "global")


def _settings() -> MagicMock:
    s = MagicMock()
    s.supabase_db_url = "postgresql://u:p@localhost/db"
    return s


def test_gold_queries_sql_has_mood_section() -> None:
    from spotify_pipeline.pipeline.gold import _SQL_GOLD_QUERIES

    assert _SQL_GOLD_QUERIES.is_file()
    raw = _SQL_GOLD_QUERIES.read_text(encoding="utf-8")
    assert "-- @@query: mood_segments" in raw
    assert "FROM music.gold_mood_segments" in raw
    assert "/*__WHERE__*/" in raw
    assert "features_found IS TRUE" in raw  # documented in comment


def test_sql_mood_segments_injects_watermark() -> None:
    sql = sql_mood_segments(_wm())
    assert "FROM music.gold_mood_segments" in sql
    assert "/*__WHERE__*/" not in sql
    assert "2026-11-12" in sql
    assert "weekly_top_songs" in sql
    assert "global" in sql


def test_mood_label_quadrants_and_unknown() -> None:
    assert _mood_label(0.8, 0.7) == "energetic"
    assert _mood_label(0.8, 0.2) == "tense"
    assert _mood_label(0.2, 0.7) == "chill"
    assert _mood_label(0.2, 0.2) == "sad"
    # boundary: high = >= 0.5
    assert _mood_label(0.5, 0.5) == "energetic"
    assert _mood_label(0.5, 0.49) == "tense"
    assert _mood_label(0.49, 0.5) == "chill"
    assert _mood_label(None, 0.7) == "unknown"
    assert _mood_label(0.7, None) == "unknown"


def test_query_mood_segments_labels_and_preserves_source() -> None:
    db = MagicMock()
    db.run.return_value = [
        (
            date(2026, 11, 12),
            "weekly_top_songs",
            "global",
            "hit1",
            "Upbeat",
            0.8,
            0.7,
            120.0,
            "reccobeats",
        ),
        (
            date(2026, 11, 12),
            "weekly_top_songs",
            "global",
            "hit2",
            None,
            None,
            0.6,
            None,
            "reccobeats",
        ),
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
        rows = query_mood_segments(_wm())

    assert rows == [
        MoodRow(
            track_id="hit1",
            track_name="Upbeat",
            energy=0.8,
            valence=0.7,
            tempo=120.0,
            source_features="reccobeats",
            mood="energetic",
        ),
        MoodRow(
            track_id="hit2",
            track_name=None,
            energy=None,
            valence=0.6,
            tempo=None,
            source_features="reccobeats",
            mood="unknown",
        ),
    ]
    sql = db.run.call_args[0][0]
    assert "FROM music.gold_mood_segments" in sql
    db.close.assert_called_once()


def test_query_mood_segments_empty_ok() -> None:
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
        assert query_mood_segments(_wm()) == []
