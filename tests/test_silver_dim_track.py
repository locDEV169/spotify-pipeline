"""Unit tests for Silver W2 dim_track metadata (Bronze → upsert; no network)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from spotify_pipeline.models.track import TrackMetadata
from spotify_pipeline.pipeline.silver import (
    SilverError,
    build_dim_track,
    fetch_latest_raw_spotify_tracks,
    upsert_dim_track_metadata_rows,
)
from spotify_pipeline.state.watermark import Watermark


def _spotify_track_payload(track_id: str = "aaa111") -> dict:
    return {
        "id": track_id,
        "name": f"Song {track_id}",
        "duration_ms": 200000,
        "explicit": False,
        "popularity": 50,
        "external_ids": {"isrc": "ISRC1"},
        "album": {
            "id": "alb1",
            "name": "Album",
            "release_date": "2021-05-05",
            "release_date_precision": "day",
        },
    }


def test_fetch_latest_raw_spotify_tracks_sql() -> None:
    conn = MagicMock()
    conn.run.return_value = [("aaa111", _spotify_track_payload())]
    got = fetch_latest_raw_spotify_tracks(conn, ["aaa111", "bbb222"])
    assert list(got) == ["aaa111"]
    sql = conn.run.call_args.args[0]
    assert "DISTINCT ON (spotify_id)" in sql
    assert "entity = 'track'" in sql
    assert "ingested_at DESC" in sql
    assert "aaa111" in sql
    assert "bbb222" in sql


def test_upsert_dim_track_metadata_sql_shape() -> None:
    track = TrackMetadata(
        track_id="aaa111",
        track_name="Song A",
        duration_ms=210000,
        explicit=False,
        album_id="alb1",
        album_name="Album A",
        release_date="2020-01-01",
        release_date_precision="day",
        isrc="USUM1",
        track_popularity=None,
    )
    conn = MagicMock()
    n = upsert_dim_track_metadata_rows(conn, [track], run_id="rid1")
    assert n == 1
    sql = conn.run.call_args.args[0]
    assert "INSERT INTO music.dim_track" in sql
    assert "ON CONFLICT (track_id)" in sql
    assert "acousticness" not in sql
    assert "features_found" not in sql
    assert "aaa111" in sql
    assert "NULL" in sql  # popularity


def test_build_dim_track_from_bronze() -> None:
    wm = Watermark.parse("2026-11-12", "weekly_top_songs", "global")
    fake_conn = MagicMock()
    fake_conn.run.side_effect = [
        [
            ("aaa111", _spotify_track_payload("aaa111")),
            ("bbb222", _spotify_track_payload("bbb222")),
        ],
        None,
        None,
    ]
    settings = MagicMock()
    settings.supabase_db_url = "postgresql://u:p@localhost/db"

    with (
        patch("spotify_pipeline.pipeline.silver.build.get_settings", return_value=settings),
        patch("spotify_pipeline.pipeline.silver.build.require_db_url"),
        patch(
            "spotify_pipeline.pipeline.silver.build.connect_postgres",
            return_value=fake_conn,
        ),
    ):
        result = build_dim_track(
            wm,
            run_id="fixed-run",
            track_ids=["aaa111", "bbb222"],
        )

    assert result.upserted == 2
    assert result.missed == 0
    assert result.track_ids == 2
    assert result.run_id == "fixed-run"
    fake_conn.close.assert_called_once()
    insert_sql = fake_conn.run.call_args_list[1].args[0]
    assert "music.dim_track" in insert_sql


def test_build_dim_track_partial_miss() -> None:
    wm = Watermark.parse("2026-11-12", "weekly_top_songs", "global")
    fake_conn = MagicMock()
    fake_conn.run.side_effect = [
        [("aaa111", _spotify_track_payload("aaa111"))],
        None,
    ]
    settings = MagicMock()
    settings.supabase_db_url = "postgresql://u:p@localhost/db"

    with (
        patch("spotify_pipeline.pipeline.silver.build.get_settings", return_value=settings),
        patch("spotify_pipeline.pipeline.silver.build.require_db_url"),
        patch(
            "spotify_pipeline.pipeline.silver.build.connect_postgres",
            return_value=fake_conn,
        ),
    ):
        result = build_dim_track(
            wm, run_id="r1", track_ids=["aaa111", "missing99"]
        )

    assert result.upserted == 1
    assert result.missed == 1


def test_build_dim_track_all_missing_fails() -> None:
    wm = Watermark.parse("2026-11-12", "weekly_top_songs", "global")
    fake_conn = MagicMock()
    fake_conn.run.return_value = []
    settings = MagicMock()
    settings.supabase_db_url = "postgresql://u:p@localhost/db"

    with (
        patch("spotify_pipeline.pipeline.silver.build.get_settings", return_value=settings),
        patch("spotify_pipeline.pipeline.silver.build.require_db_url"),
        patch(
            "spotify_pipeline.pipeline.silver.build.connect_postgres",
            return_value=fake_conn,
        ),
        pytest.raises(SilverError, match="no Bronze raw_spotify track"),
    ):
        build_dim_track(wm, track_ids=["aaa111"])


def test_build_dim_track_idempotent_sql() -> None:
    wm = Watermark.parse("2026-11-12", "weekly_top_songs", "global")
    fake_conn = MagicMock()
    payload_row = [("aaa111", _spotify_track_payload("aaa111"))]
    fake_conn.run.side_effect = [payload_row, None, payload_row, None]
    settings = MagicMock()
    settings.supabase_db_url = "postgresql://u:p@localhost/db"

    with (
        patch("spotify_pipeline.pipeline.silver.build.get_settings", return_value=settings),
        patch("spotify_pipeline.pipeline.silver.build.require_db_url"),
        patch(
            "spotify_pipeline.pipeline.silver.build.connect_postgres",
            return_value=fake_conn,
        ),
    ):
        a = build_dim_track(wm, run_id="r1", track_ids=["aaa111"])
        b = build_dim_track(wm, run_id="r2", track_ids=["aaa111"])

    assert a.upserted == b.upserted == 1
    inserts = [
        c.args[0]
        for c in fake_conn.run.call_args_list
        if "INSERT INTO music.dim_track" in c.args[0]
    ]
    assert len(inserts) == 2
    assert all("ON CONFLICT (track_id)" in sql for sql in inserts)
    assert all("bridge_" not in sql for sql in inserts)
