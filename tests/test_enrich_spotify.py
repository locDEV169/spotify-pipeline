"""Unit tests for C9 enrich_spotify (Bronze IDs + mocked network/DB)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from spotify_pipeline.pipeline.enrich.spotify import EnrichSpotifyError, enrich_spotify
from spotify_pipeline.pipeline.bronze.extract_ids import ExtractIdsError, ExtractedIds
from spotify_pipeline.state.watermark import Watermark


def test_enrich_spotify_writes_track_and_artists_from_bronze() -> None:
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
    extracted = ExtractedIds(
        track_ids=["aaa111"],
        artist_ids=[],
        watermark=wm.as_tuple(),
        raw_charts_id=1,
    )

    with (
        patch(
            "spotify_pipeline.pipeline.enrich.spotify.extract_ids",
            return_value=extracted,
        ) as extract,
        patch("spotify_pipeline.pipeline.enrich.spotify.get_settings", return_value=settings),
        patch("spotify_pipeline.pipeline.enrich.spotify.require_db_url"),
        patch(
            "spotify_pipeline.pipeline.enrich.spotify.connect_postgres",
            return_value=fake_conn,
        ),
        patch(
            "spotify_pipeline.pipeline.enrich.spotify.call_with_db_retry",
            side_effect=lambda db_url, conn, fn: (fn(conn), conn)[1],
        ),
        patch(
            "spotify_pipeline.pipeline.enrich.spotify.get_access_token",
            return_value={"access_token": "tok"},
        ),
        patch(
            "spotify_pipeline.pipeline.enrich.spotify.get_track",
            return_value=track_payload,
        ) as get_track,
        patch(
            "spotify_pipeline.pipeline.enrich.spotify.get_artist",
            side_effect=lambda token, aid, client=None: {"id": aid, "name": aid},
        ) as get_artist,
        patch("spotify_pipeline.pipeline.enrich.spotify.write_raw_spotify") as write_raw,
        patch("spotify_pipeline.pipeline.enrich.spotify.httpx.Client"),
    ):
        result = enrich_spotify(wm, run_id="run123", write_fs=False)

    extract.assert_called_once_with(wm)
    assert result["run_id"] == "run123"
    assert result["track_count"] == 1
    assert result["artist_count"] == 2
    assert result["inserted"] == 3
    get_track.assert_called_once()
    assert get_artist.call_count == 2
    assert write_raw.call_count == 3
    fake_conn.close.assert_called_once()


def test_enrich_spotify_accepts_injected_ids() -> None:
    wm = Watermark.parse("2026-11-12", "weekly_top_songs", "global")
    fake_conn = MagicMock()
    settings = MagicMock()
    settings.supabase_db_url = "postgresql://u:p@localhost/db"
    settings.bronze_dir = None
    settings.spotify_client_id = "cid"
    settings.spotify_client_secret = "sec"

    with (
        patch("spotify_pipeline.pipeline.enrich.spotify.extract_ids") as extract,
        patch("spotify_pipeline.pipeline.enrich.spotify.get_settings", return_value=settings),
        patch("spotify_pipeline.pipeline.enrich.spotify.require_db_url"),
        patch(
            "spotify_pipeline.pipeline.enrich.spotify.connect_postgres",
            return_value=fake_conn,
        ),
        patch(
            "spotify_pipeline.pipeline.enrich.spotify.call_with_db_retry",
            side_effect=lambda db_url, conn, fn: (fn(conn), conn)[1],
        ),
        patch(
            "spotify_pipeline.pipeline.enrich.spotify.get_access_token",
            return_value={"access_token": "tok"},
        ),
        patch(
            "spotify_pipeline.pipeline.enrich.spotify.get_track",
            return_value={"id": "t1", "artists": []},
        ),
        patch("spotify_pipeline.pipeline.enrich.spotify.write_raw_spotify"),
        patch("spotify_pipeline.pipeline.enrich.spotify.httpx.Client"),
    ):
        result = enrich_spotify(
            wm, run_id="inj", write_fs=False, track_ids=["t1"], artist_ids=[]
        )

    extract.assert_not_called()
    assert result["track_count"] == 1
    assert result["inserted"] == 1


def test_enrich_spotify_missing_bronze() -> None:
    wm = Watermark.parse("2026-11-12", "weekly_top_songs", "global")
    settings = MagicMock()
    settings.supabase_db_url = "postgresql://u:p@localhost/db"
    settings.spotify_client_id = "cid"
    settings.spotify_client_secret = "sec"

    with (
        patch(
            "spotify_pipeline.pipeline.enrich.spotify.extract_ids",
            side_effect=ExtractIdsError("no Bronze raw_charts for watermark"),
        ),
        patch("spotify_pipeline.pipeline.enrich.spotify.get_settings", return_value=settings),
        patch("spotify_pipeline.pipeline.enrich.spotify.require_db_url"),
        pytest.raises(EnrichSpotifyError, match="no Bronze"),
    ):
        enrich_spotify(wm, write_fs=False)
