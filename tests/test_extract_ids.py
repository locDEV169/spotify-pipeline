"""Unit tests for Stage 4 extract_ids (Bronze → track/artist IDs)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from spotify_pipeline.pipeline.extract_ids import (
    ExtractIdsError,
    extract_ids,
    ids_from_bronze_payload,
)
from spotify_pipeline.state.watermark import Watermark


def _songs_bronze_payload() -> dict:
    return {
        "displayChart": {"date": "2026-11-12"},
        "entries": [
            {
                "chartEntryData": {"currentRank": 1, "previousRank": 2},
                "trackMetadata": {"trackUri": "spotify:track:aaa111"},
            },
            {
                "chartEntryData": {"currentRank": 2},
                "trackMetadata": {"trackUri": "spotify:track:bbb222"},
            },
        ],
    }


def _artists_bronze_payload() -> dict:
    return {
        "displayChart": {"date": "2026-11-12"},
        "entries": [
            {
                "artistMetadata": {"artistUri": "spotify:artist:art001"},
            },
            {
                "artistMetadata": {"artistUri": "spotify:artist:art002"},
            },
        ],
    }


def test_ids_from_bronze_payload_songs() -> None:
    wm = Watermark.parse("2026-11-12", "weekly_top_songs", "global")
    got = ids_from_bronze_payload(wm, _songs_bronze_payload(), raw_charts_id=9)
    assert got.track_ids == ["aaa111", "bbb222"]
    assert got.artist_ids == []
    assert got.raw_charts_id == 9


def test_ids_from_bronze_payload_artists() -> None:
    wm = Watermark.parse("2026-11-12", "weekly_top_artists", "global")
    got = ids_from_bronze_payload(wm, _artists_bronze_payload())
    assert got.track_ids == []
    assert got.artist_ids == ["art001", "art002"]


def test_extract_ids_reads_latest_raw_charts() -> None:
    wm = Watermark.parse("2026-11-12", "weekly_top_songs", "global")
    fake_conn = MagicMock()
    fake_conn.run.return_value = [(42, _songs_bronze_payload())]
    settings = MagicMock()
    settings.supabase_db_url = "postgresql://u:p@localhost/db"

    with (
        patch("spotify_pipeline.pipeline.extract_ids.get_settings", return_value=settings),
        patch("spotify_pipeline.pipeline.extract_ids.require_db_url"),
        patch(
            "spotify_pipeline.pipeline.extract_ids.connect_postgres",
            return_value=fake_conn,
        ),
    ):
        got = extract_ids(wm)

    assert got.track_ids == ["aaa111", "bbb222"]
    assert got.raw_charts_id == 42
    fake_conn.close.assert_called_once()
    sql = fake_conn.run.call_args.args[0]
    assert "music.raw_charts" in sql
    assert "2026-11-12" in sql
    assert "weekly_top_songs" in sql


def test_extract_ids_missing_bronze_row() -> None:
    wm = Watermark.parse("2026-11-12", "weekly_top_songs", "global")
    fake_conn = MagicMock()
    fake_conn.run.return_value = []
    settings = MagicMock()
    settings.supabase_db_url = "postgresql://u:p@localhost/db"

    with (
        patch("spotify_pipeline.pipeline.extract_ids.get_settings", return_value=settings),
        patch("spotify_pipeline.pipeline.extract_ids.require_db_url"),
        patch(
            "spotify_pipeline.pipeline.extract_ids.connect_postgres",
            return_value=fake_conn,
        ),
        pytest.raises(ExtractIdsError, match="no Bronze raw_charts"),
    ):
        extract_ids(wm)
