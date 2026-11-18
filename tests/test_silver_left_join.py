"""W5 — LEFT JOIN read path + COALESCE upsert semantics (no network)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from spotify_pipeline.models.audio_features import AudioFeatures
from spotify_pipeline.models.track import TrackMetadata
from spotify_pipeline.pipeline.silver import (
    build_silver,
    mark_dim_track_features_misses,
    sql_fact_chart_left_join_dim_track,
    upsert_dim_track_features_rows,
    upsert_dim_track_metadata_rows,
)
from spotify_pipeline.state.watermark import Watermark


def test_sql_fact_chart_left_join_never_inner() -> None:
    wm = Watermark.parse("2026-11-12", "weekly_top_songs", "global")
    sql = sql_fact_chart_left_join_dim_track(wm)
    assert "LEFT JOIN music.dim_track" in sql
    assert "INNER JOIN" not in sql
    assert "2026-11-12" in sql
    assert "FROM music.fact_chart" in sql
    assert "/*__WHERE__*/" not in sql


def test_sql_fact_chart_left_join_loads_from_docs_sql_file() -> None:
    from spotify_pipeline.pipeline.silver import _SQL_FACT_LEFT_JOIN

    assert _SQL_FACT_LEFT_JOIN.is_file()
    raw = _SQL_FACT_LEFT_JOIN.read_text(encoding="utf-8")
    assert "LEFT JOIN music.dim_track" in raw
    assert "/*__WHERE__*/" in raw
    # no watermark → placeholder removed, no WHERE clause injected
    sql = sql_fact_chart_left_join_dim_track(None)
    assert "WHERE f.chart_date" not in sql
    assert "LEFT JOIN music.dim_track" in sql


def test_metadata_upsert_does_not_touch_feature_columns() -> None:
    track = TrackMetadata(
        track_id="aaa111",
        track_name="Song",
        duration_ms=1000,
        explicit=False,
        album_id=None,
        album_name=None,
        release_date=None,
        release_date_precision=None,
        isrc="ISRC1",
        track_popularity=10,
    )
    conn = MagicMock()
    upsert_dim_track_metadata_rows(conn, [track], run_id="r1")
    sql = conn.run.call_args.args[0]
    for col in (
        "acousticness",
        "danceability",
        "energy",
        "features_found",
        "features_fetched_at",
        "source_features",
        "reccobeats_uuid",
    ):
        assert col not in sql


def test_features_upsert_coalesce_preserves_metadata_side() -> None:
    feat = AudioFeatures(
        track_id="aaa111",
        reccobeats_uuid="uuid-1",
        href="https://open.spotify.com/track/aaa111",
        energy=0.8,
        valence=0.4,
        features_found=True,
    )
    conn = MagicMock()
    upsert_dim_track_features_rows(conn, [feat], run_id="r1")
    sql = conn.run.call_args.args[0]
    assert "COALESCE(EXCLUDED.energy, dim_track.energy)" in sql
    assert "track_name" not in sql
    assert "album_name" not in sql
    assert "features_found      = EXCLUDED.features_found" in sql


def test_feature_miss_update_never_deletes_fact_chart() -> None:
    conn = MagicMock()
    mark_dim_track_features_misses(conn, ["bbb222"], run_id="r1")
    sql = conn.run.call_args.args[0]
    assert "UPDATE music.dim_track" in sql
    assert "features_found = FALSE" in sql
    assert "DELETE" not in sql.upper()
    assert "fact_chart" not in sql


def test_build_silver_one_pass_orchestrates_builders() -> None:
    wm = Watermark.parse("2026-11-12", "weekly_top_songs", "global")
    fake_conn = MagicMock()
    settings = MagicMock()
    settings.supabase_db_url = "postgresql://u:p@localhost/db"

    fact = MagicMock(upserted=2, raw_charts_id=1, watermark=wm.as_tuple(), run_id="rid")
    dim = MagicMock(upserted=2, missed=0, track_ids=2, watermark=wm.as_tuple(), run_id="rid")
    artists = MagicMock(
        artists_upserted=1,
        bridges_upserted=1,
        artists_missed=0,
        watermark=wm.as_tuple(),
        run_id="rid",
    )
    features = MagicMock(
        hits=1, misses=1, track_ids=2, watermark=wm.as_tuple(), run_id="rid"
    )

    with (
        patch("spotify_pipeline.pipeline.silver.get_settings", return_value=settings),
        patch("spotify_pipeline.pipeline.silver.require_db_url"),
        patch(
            "spotify_pipeline.pipeline.silver.connect_postgres",
            return_value=fake_conn,
        ),
        patch(
            "spotify_pipeline.pipeline.silver.build_fact_chart",
            return_value=fact,
        ) as m_fact,
        patch(
            "spotify_pipeline.pipeline.silver.build_dim_track",
            return_value=dim,
        ) as m_dim,
        patch(
            "spotify_pipeline.pipeline.silver.build_dim_artist_bridge",
            return_value=artists,
        ) as m_art,
        patch(
            "spotify_pipeline.pipeline.silver.build_dim_track_features",
            return_value=features,
        ) as m_feat,
    ):
        result = build_silver(wm, run_id="rid")

    assert result.run_id == "rid"
    assert result.fact is fact
    assert result.dim_track is dim
    assert result.artist_bridge is artists
    assert result.features is features
    m_fact.assert_called_once()
    m_dim.assert_called_once()
    m_art.assert_called_once()
    m_feat.assert_called_once()
    # Shared connection: builders must not open a second conn when conn passed.
    assert m_fact.call_args.kwargs.get("conn") is fake_conn
    assert m_dim.call_args.kwargs.get("run_id") == "rid"
    fake_conn.close.assert_called_once()
