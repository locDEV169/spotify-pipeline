"""Unit tests for C9 enrich_reccobeats (Bronze IDs + mocked network/DB)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from spotify_pipeline.pipeline.enrich_reccobeats import (
    EnrichReccoBeatsError,
    enrich_reccobeats,
)
from spotify_pipeline.pipeline.extract_ids import ExtractedIds
from spotify_pipeline.state.watermark import Watermark


def test_enrich_reccobeats_batches_and_writes() -> None:
    wm = Watermark.parse("2026-11-12", "weekly_top_songs", "global")
    fake_conn = MagicMock()
    settings = MagicMock()
    settings.supabase_db_url = "postgresql://u:p@localhost/db"
    settings.bronze_dir = None
    settings.reccobeats_batch_size = 40
    extracted = ExtractedIds(
        track_ids=["id00", "id01"],
        artist_ids=[],
        watermark=wm.as_tuple(),
    )
    features = {
        "content": [
            {"href": "https://open.spotify.com/track/id00"},
        ]
    }

    with (
        patch(
            "spotify_pipeline.pipeline.enrich_reccobeats.extract_ids",
            return_value=extracted,
        ) as extract,
        patch(
            "spotify_pipeline.pipeline.enrich_reccobeats.get_settings",
            return_value=settings,
        ),
        patch("spotify_pipeline.pipeline.enrich_reccobeats.require_db_url"),
        patch(
            "spotify_pipeline.pipeline.enrich_reccobeats.connect_postgres",
            return_value=fake_conn,
        ),
        patch(
            "spotify_pipeline.pipeline.enrich_reccobeats.call_with_db_retry",
            side_effect=lambda db_url, conn, fn: (fn(conn), conn)[1],
        ),
        patch(
            "spotify_pipeline.pipeline.enrich_reccobeats.get_audio_features",
            return_value=features,
        ) as get_af,
        patch(
            "spotify_pipeline.pipeline.enrich_reccobeats.write_raw_reccobeats"
        ) as write_raw,
        patch("spotify_pipeline.pipeline.enrich_reccobeats.httpx.Client"),
    ):
        result = enrich_reccobeats(wm, run_id="run456", write_fs=False)

    extract.assert_called_once_with(wm)
    assert result["run_id"] == "run456"
    assert result["track_count"] == 2
    assert result["batch_count"] == 1
    assert result["hits"] == 1
    assert result["misses"] == 1
    assert result["inserted"] == 1
    get_af.assert_called_once()
    assert len(get_af.call_args.args[0]) <= 40
    write_raw.assert_called_once()
    assert write_raw.call_args.kwargs["bronze_dir"] is None
    fake_conn.close.assert_called_once()


def test_enrich_reccobeats_chunks_over_40() -> None:
    wm = Watermark.parse("2026-11-12", "weekly_top_songs", "global")
    fake_conn = MagicMock()
    settings = MagicMock()
    settings.supabase_db_url = "postgresql://u:p@localhost/db"
    settings.bronze_dir = None
    settings.reccobeats_batch_size = 40
    extracted = ExtractedIds(
        track_ids=[f"id{i:02d}" for i in range(45)],
        artist_ids=[],
        watermark=wm.as_tuple(),
    )

    with (
        patch(
            "spotify_pipeline.pipeline.enrich_reccobeats.extract_ids",
            return_value=extracted,
        ),
        patch(
            "spotify_pipeline.pipeline.enrich_reccobeats.get_settings",
            return_value=settings,
        ),
        patch("spotify_pipeline.pipeline.enrich_reccobeats.require_db_url"),
        patch(
            "spotify_pipeline.pipeline.enrich_reccobeats.connect_postgres",
            return_value=fake_conn,
        ),
        patch(
            "spotify_pipeline.pipeline.enrich_reccobeats.call_with_db_retry",
            side_effect=lambda db_url, conn, fn: (fn(conn), conn)[1],
        ),
        patch(
            "spotify_pipeline.pipeline.enrich_reccobeats.get_audio_features",
            return_value={"content": []},
        ) as get_af,
        patch("spotify_pipeline.pipeline.enrich_reccobeats.write_raw_reccobeats"),
        patch("spotify_pipeline.pipeline.enrich_reccobeats.httpx.Client"),
    ):
        result = enrich_reccobeats(wm, run_id="run789", write_fs=False)

    assert result["batch_count"] == 2
    assert result["inserted"] == 2
    assert get_af.call_count == 2
    for call in get_af.call_args_list:
        assert len(call.args[0]) <= 40


def test_enrich_reccobeats_rejects_artists_chart() -> None:
    wm = Watermark.parse("2026-11-12", "weekly_top_artists", "global")
    with pytest.raises(EnrichReccoBeatsError, match="weekly_top_songs"):
        enrich_reccobeats(wm, write_fs=False)


def test_enrich_reccobeats_injected_ids_skips_extract() -> None:
    wm = Watermark.parse("2026-11-12", "weekly_top_songs", "global")
    fake_conn = MagicMock()
    settings = MagicMock()
    settings.supabase_db_url = "postgresql://u:p@localhost/db"
    settings.bronze_dir = None
    settings.reccobeats_batch_size = 40

    with (
        patch("spotify_pipeline.pipeline.enrich_reccobeats.extract_ids") as extract,
        patch(
            "spotify_pipeline.pipeline.enrich_reccobeats.get_settings",
            return_value=settings,
        ),
        patch("spotify_pipeline.pipeline.enrich_reccobeats.require_db_url"),
        patch(
            "spotify_pipeline.pipeline.enrich_reccobeats.connect_postgres",
            return_value=fake_conn,
        ),
        patch(
            "spotify_pipeline.pipeline.enrich_reccobeats.call_with_db_retry",
            side_effect=lambda db_url, conn, fn: (fn(conn), conn)[1],
        ),
        patch(
            "spotify_pipeline.pipeline.enrich_reccobeats.get_audio_features",
            return_value={"content": []},
        ),
        patch("spotify_pipeline.pipeline.enrich_reccobeats.write_raw_reccobeats"),
        patch("spotify_pipeline.pipeline.enrich_reccobeats.httpx.Client"),
    ):
        result = enrich_reccobeats(
            wm, run_id="inj", write_fs=False, track_ids=["a", "b"]
        )

    extract.assert_not_called()
    assert result["track_count"] == 2
    assert result["inserted"] == 1
