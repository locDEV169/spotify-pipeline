"""Unit tests for C9 enrich_reccobeats (mocked network/DB)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from spotify_pipeline.pipeline.enrich_reccobeats import (
    EnrichReccoBeatsError,
    enrich_reccobeats,
)
from spotify_pipeline.state.watermark import Watermark


def _songs_payload(chart_date: str = "2026-11-12", n: int = 2) -> dict:
    entries = [
        {
            "chartEntryData": {"currentRank": i + 1},
            "trackMetadata": {"trackUri": f"spotify:track:id{i:02d}"},
        }
        for i in range(n)
    ]
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
                "entries": entries,
            }
        ]
    }


def test_enrich_reccobeats_batches_and_writes() -> None:
    wm = Watermark.parse("2026-11-12", "weekly_top_songs", "global")
    fake_conn = MagicMock()
    settings = MagicMock()
    settings.supabase_db_url = "postgresql://u:p@localhost/db"
    settings.bronze_dir = None
    settings.reccobeats_batch_size = 40

    features = {
        "content": [
            {"href": "https://open.spotify.com/track/id00"},
        ]
    }

    with (
        patch(
            "spotify_pipeline.pipeline.enrich_reccobeats.fetch_public_charts",
            return_value=_songs_payload(n=2),
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
            return_value=features,
        ) as get_af,
        patch(
            "spotify_pipeline.pipeline.enrich_reccobeats.write_raw_reccobeats"
        ) as write_raw,
        patch("spotify_pipeline.pipeline.enrich_reccobeats.httpx.Client"),
    ):
        result = enrich_reccobeats(wm, run_id="run456", write_fs=False)

    assert result["run_id"] == "run456"
    assert result["track_count"] == 2
    assert result["batch_count"] == 1
    assert result["hits"] == 1
    assert result["misses"] == 1
    assert result["inserted"] == 1
    get_af.assert_called_once()
    called_ids = get_af.call_args.args[0]
    assert len(called_ids) <= 40
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

    with (
        patch(
            "spotify_pipeline.pipeline.enrich_reccobeats.fetch_public_charts",
            return_value=_songs_payload(n=45),
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


def test_enrich_reccobeats_rejects_watermark_mismatch() -> None:
    wm = Watermark.parse("2020-01-01", "weekly_top_songs", "global")
    settings = MagicMock()
    settings.supabase_db_url = "postgresql://u:p@localhost/db"
    settings.bronze_dir = None
    settings.reccobeats_batch_size = 40

    with (
        patch(
            "spotify_pipeline.pipeline.enrich_reccobeats.fetch_public_charts",
            return_value=_songs_payload("2026-11-12"),
        ),
        patch(
            "spotify_pipeline.pipeline.enrich_reccobeats.get_settings",
            return_value=settings,
        ),
        patch("spotify_pipeline.pipeline.enrich_reccobeats.require_db_url"),
        patch("spotify_pipeline.pipeline.enrich_reccobeats.httpx.Client"),
        pytest.raises(EnrichReccoBeatsError, match="mismatch"),
    ):
        enrich_reccobeats(wm, write_fs=False)
