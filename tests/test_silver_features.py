"""Unit tests for Silver W4 ReccoBeats → features_found (no network)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from spotify_pipeline.models.audio_features import (
    AudioFeatures,
    audio_features_from_reccobeats_item,
)
from spotify_pipeline.pipeline.silver import (
    build_dim_track_features,
    fetch_reccobeats_features_by_track_id,
    mark_dim_track_features_misses,
    upsert_dim_track_features_rows,
)
from spotify_pipeline.state.watermark import Watermark


def _rb_item(spotify_id: str, uuid: str = "uuid-1") -> dict:
    return {
        "id": uuid,
        "href": f"https://open.spotify.com/track/{spotify_id}",
        "acousticness": 0.1,
        "danceability": 0.2,
        "energy": 0.3,
        "instrumentalness": 0.0,
        "liveness": 0.1,
        "speechiness": 0.05,
        "valence": 0.5,
        "loudness": -5.0,
        "tempo": 120.0,
        "key": 1,
        "mode": 1,
    }


def test_audio_features_from_reccobeats_item() -> None:
    feat = audio_features_from_reccobeats_item(_rb_item("aaa111", "rb-uuid"))
    assert feat.track_id == "aaa111"
    assert feat.reccobeats_uuid == "rb-uuid"
    assert feat.features_found is True
    assert feat.energy == 0.3


def test_fetch_reccobeats_features_by_track_id() -> None:
    conn = MagicMock()
    conn.run.return_value = [
        ({"content": [_rb_item("aaa111"), _rb_item("ccc333", "u3")]},),
    ]
    got = fetch_reccobeats_features_by_track_id(conn, ["aaa111", "bbb222", "ccc333"])
    assert set(got) == {"aaa111", "ccc333"}
    sql = conn.run.call_args.args[0]
    assert "music.raw_reccobeats" in sql
    assert "spotify_track_ids &&" in sql


def test_upsert_features_and_miss_sql() -> None:
    conn = MagicMock()
    feat = audio_features_from_reccobeats_item(_rb_item("aaa111"))
    assert upsert_dim_track_features_rows(conn, [feat], run_id="r1") == 1
    assert mark_dim_track_features_misses(conn, ["bbb222"], run_id="r1") == 1
    hit_sql = conn.run.call_args_list[0].args[0]
    miss_sql = conn.run.call_args_list[1].args[0]
    assert "INSERT INTO music.dim_track" in hit_sql
    assert "features_found" in hit_sql
    assert "TRUE" in hit_sql
    assert "source_features" in hit_sql
    assert "reccobeats" in hit_sql
    assert "UPDATE music.dim_track" in miss_sql
    assert "features_found = FALSE" in miss_sql
    assert "DELETE" not in miss_sql
    assert "fact_chart" not in miss_sql


def test_build_dim_track_features_hits_and_misses() -> None:
    wm = Watermark.parse("2026-11-12", "weekly_top_songs", "global")
    fake_conn = MagicMock()
    # SELECT raw_reccobeats → INSERT hit → UPDATE miss
    fake_conn.run.side_effect = [
        [({"content": [_rb_item("aaa111")]},)],
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
        result = build_dim_track_features(
            wm, run_id="fixed", track_ids=["aaa111", "bbb222"]
        )

    assert result.hits == 1
    assert result.misses == 1
    assert result.track_ids == 2
