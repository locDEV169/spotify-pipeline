"""Unit tests for Silver W3 dim_artist + bridge (no network)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from spotify_pipeline.models.track import (
    ArtistMetadata,
    TrackArtistLink,
    artist_from_spotify_payload,
    bridge_links_from_track_payload,
)
from spotify_pipeline.pipeline.silver import (
    SilverError,
    build_dim_artist_bridge,
    upsert_bridge_track_artist_rows,
    upsert_dim_artist_rows,
)
from spotify_pipeline.state.watermark import Watermark


def _track_with_artists() -> dict:
    return {
        "id": "trk1",
        "name": "Song",
        "artists": [
            {"id": "artA", "name": "Artist A"},
            {"id": "artB", "name": "Artist B"},
        ],
    }


def _artist_payload(artist_id: str = "artA") -> dict:
    return {
        "id": artist_id,
        "name": f"Name {artist_id}",
        "genres": ["pop"],
        "followers": {"total": 10},
        "popularity": 40,
    }


def test_bridge_links_0_based_multi_artist() -> None:
    links = bridge_links_from_track_payload(_track_with_artists())
    assert [(l.artist_id, l.artist_position) for l in links] == [
        ("artA", 0),
        ("artB", 1),
    ]


def test_artist_from_spotify_payload_nullable_fields() -> None:
    row = artist_from_spotify_payload(
        {"id": "artA", "name": "A", "genres": [], "followers": {}}
    )
    assert row.artist_id == "artA"
    assert row.genres == []
    assert row.followers is None
    assert row.artist_popularity is None


def test_upsert_dim_artist_and_bridge_sql() -> None:
    conn = MagicMock()
    artists = [
        ArtistMetadata(
            artist_id="artA",
            artist_name="A",
            genres=["pop"],
            followers=1,
            artist_popularity=None,
        )
    ]
    links = [TrackArtistLink(track_id="trk1", artist_id="artA", artist_position=0)]
    assert upsert_dim_artist_rows(conn, artists, run_id="r1") == 1
    assert upsert_bridge_track_artist_rows(conn, links) == 1
    artist_sql = conn.run.call_args_list[0].args[0]
    bridge_sql = conn.run.call_args_list[1].args[0]
    assert "INSERT INTO music.dim_artist" in artist_sql
    assert "ON CONFLICT (artist_id)" in artist_sql
    assert "INSERT INTO music.bridge_track_artist" in bridge_sql
    assert "ON CONFLICT (track_id, artist_id)" in bridge_sql


def test_build_dim_artist_bridge() -> None:
    wm = Watermark.parse("2026-11-12", "weekly_top_songs", "global")
    fake_conn = MagicMock()
    fake_conn.run.side_effect = [
        [("trk1", _track_with_artists())],  # tracks
        [
            ("artA", _artist_payload("artA")),
            ("artB", _artist_payload("artB")),
        ],  # artists
        None,  # artist upsert A
        None,  # artist upsert B
        None,  # bridge A
        None,  # bridge B
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
        result = build_dim_artist_bridge(
            wm, run_id="fixed", track_ids=["trk1"]
        )

    assert result.artists_upserted == 2
    assert result.bridges_upserted == 2
    assert result.artists_missed == 0


def test_build_dim_artist_bridge_embedded_fallback() -> None:
    wm = Watermark.parse("2026-11-12", "weekly_top_songs", "global")
    fake_conn = MagicMock()
    fake_conn.run.side_effect = [
        [("trk1", _track_with_artists())],
        [],  # no raw_spotify artists
        None,
        None,
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
        result = build_dim_artist_bridge(
            wm, run_id="fixed", track_ids=["trk1"]
        )

    assert result.artists_upserted == 2
    assert result.artists_missed == 2
    assert result.bridges_upserted == 2


def test_build_dim_artist_bridge_no_links_fails() -> None:
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
        pytest.raises(SilverError, match="no track.artists"),
    ):
        build_dim_artist_bridge(wm, track_ids=["trk1"])
