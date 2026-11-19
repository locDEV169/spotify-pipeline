"""SPEC C10 — Silver package (fact/dims builders + LEFT JOIN helper).

Public import path unchanged: `spotify_pipeline.pipeline.silver`.
"""

from spotify_pipeline.pipeline.silver.build import (
    ArtistBridgeBuildResult,
    DimTrackBuildResult,
    FactChartBuildResult,
    FeaturesBuildResult,
    SilverBuildResult,
    SilverError,
    _SQL_FACT_LEFT_JOIN,
    build_dim_artist_bridge,
    build_dim_track,
    build_dim_track_features,
    build_fact_chart,
    build_silver,
    fact_entries_from_bronze_payload,
    fetch_latest_raw_spotify_tracks,
    fetch_reccobeats_features_by_track_id,
    mark_dim_track_features_misses,
    sql_fact_chart_left_join_dim_track,
    upsert_bridge_track_artist_rows,
    upsert_dim_artist_rows,
    upsert_dim_track_features_rows,
    upsert_dim_track_metadata_rows,
    upsert_fact_chart_rows,
)

__all__ = [
    "ArtistBridgeBuildResult",
    "DimTrackBuildResult",
    "FactChartBuildResult",
    "FeaturesBuildResult",
    "SilverBuildResult",
    "SilverError",
    "_SQL_FACT_LEFT_JOIN",
    "build_dim_artist_bridge",
    "build_dim_track",
    "build_dim_track_features",
    "build_fact_chart",
    "build_silver",
    "fact_entries_from_bronze_payload",
    "fetch_latest_raw_spotify_tracks",
    "fetch_reccobeats_features_by_track_id",
    "mark_dim_track_features_misses",
    "sql_fact_chart_left_join_dim_track",
    "upsert_bridge_track_artist_rows",
    "upsert_dim_artist_rows",
    "upsert_dim_track_features_rows",
    "upsert_dim_track_metadata_rows",
    "upsert_fact_chart_rows",
]
