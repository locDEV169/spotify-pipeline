"""Unit tests for C9 enrich_spotify (mocked network/DB)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from spotify_pipeline.pipeline.enrich_spotify import EnrichSpotifyError, enrich_spotify
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
                        "chartEntryData": {"currentRank": 1},
                        "trackMetadata": {"trackUri": "spotify:track:aaa111"},
                    }
                ],
            }
        ]
    }


def test_enrich_spotify_writes_track_and_artists() -> None:
    wm = Watermark.parse("2026-11-12", "weekly_top_songs", "global")
    fake_conn = MagicMock()
    settings = MagicMock()
    settings.supabase_db_url = "postgresql://u:p@localhost/db"
    settings.bronze_dir = None
    settings.spotify_client_id = "cid"
    settings.spotify_client_secret = "sec"

    track_payload = {
        "id": "aaa111",
        "name": "Song",
        "artists": [{"id": "art1", "name": "A"}, {"id": "art2", "name": "B"}],
    }

    with (
        patch(
            "spotify_pipeline.pipeline.enrich_spotify.fetch_public_charts",
            return_value=_songs_payload(),
        ),
        patch("spotify_pipeline.pipeline.enrich_spotify.get_settings", return_value=settings),
        patch("spotify_pipeline.pipeline.enrich_spotify.require_db_url"),
        patch(
            "spotify_pipeline.pipeline.enrich_spotify.connect_postgres",
            return_value=fake_conn,
        ),
        patch(
            "spotify_pipeline.pipeline.enrich_spotify.call_with_db_retry",
            side_effect=lambda db_url, conn, fn: (fn(conn), conn)[1],
        ),
        patch(
            "spotify_pipeline.pipeline.enrich_spotify.get_access_token",
            return_value={"access_token": "tok"},
        ),
        patch(
            "spotify_pipeline.pipeline.enrich_spotify.get_track",
            return_value=track_payload,
        ) as get_track,
        patch(
            "spotify_pipeline.pipeline.enrich_spotify.get_artist",
            side_effect=lambda token, aid, client=None: {"id": aid, "name": aid},
        ) as get_artist,
        patch("spotify_pipeline.pipeline.enrich_spotify.write_raw_spotify") as write_raw,
        patch("spotify_pipeline.pipeline.enrich_spotify.httpx.Client"),
    ):
        result = enrich_spotify(wm, run_id="run123", write_fs=False)

    assert result["run_id"] == "run123"
    assert result["track_count"] == 1
    assert result["artist_count"] == 2
    assert result["inserted"] == 3
    get_track.assert_called_once()
    assert get_artist.call_count == 2
    assert write_raw.call_count == 3
    entities = [c.kwargs["entity"] for c in write_raw.call_args_list]
    assert entities == ["track", "artist", "artist"]
    assert all(c.kwargs["bronze_dir"] is None for c in write_raw.call_args_list)
    fake_conn.close.assert_called_once()


def test_enrich_spotify_rejects_watermark_mismatch() -> None:
    wm = Watermark.parse("2020-01-01", "weekly_top_songs", "global")
    settings = MagicMock()
    settings.supabase_db_url = "postgresql://u:p@localhost/db"
    settings.bronze_dir = None
    settings.spotify_client_id = "cid"
    settings.spotify_client_secret = "sec"

    with (
        patch(
            "spotify_pipeline.pipeline.enrich_spotify.fetch_public_charts",
            return_value=_songs_payload("2026-11-12"),
        ),
        patch("spotify_pipeline.pipeline.enrich_spotify.get_settings", return_value=settings),
        patch("spotify_pipeline.pipeline.enrich_spotify.require_db_url"),
        patch("spotify_pipeline.pipeline.enrich_spotify.httpx.Client"),
        pytest.raises(EnrichSpotifyError, match="mismatch"),
    ):
        enrich_spotify(wm, write_fs=False)
