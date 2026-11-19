"""SPEC C11 — Gold package (readers + SQL + one-pass build).

Public import path unchanged: `spotify_pipeline.pipeline.gold`.
SQL check/build: `spotify_pipeline.pipeline.gold.sql`.

G5 (GQ-5): formal SCD2 deferred — see `build.SCD2_STATUS`.
"""

from spotify_pipeline.pipeline.gold.build import (
    SCD2_STATUS,
    GoldBuildResult,
    build_gold,
)
from spotify_pipeline.pipeline.gold.readers import (
    FeatureCoverageReport,
    FeatureCoverageResult,
    MissingFeatureRow,
    MoodRow,
    MoverRow,
    PopularityFeaturePair,
    PopularityFeatureResult,
    get_feature_coverage_report,
    query_feature_coverage,
    query_missing_features,
    query_mood_segments,
    query_movers,
    query_popularity_feature_pairs,
)
from spotify_pipeline.pipeline.gold.sql import (
    SQL_GOLD_QUERIES,
    GoldError,
    sql_feature_coverage,
    sql_missing_features,
    sql_mood_segments,
    sql_movers,
    sql_popularity_feature_pairs,
)

# Tests historically import this private name.
_SQL_GOLD_QUERIES = SQL_GOLD_QUERIES

__all__ = [
    "SCD2_STATUS",
    "SQL_GOLD_QUERIES",
    "_SQL_GOLD_QUERIES",
    "FeatureCoverageReport",
    "FeatureCoverageResult",
    "GoldBuildResult",
    "GoldError",
    "MissingFeatureRow",
    "MoodRow",
    "MoverRow",
    "PopularityFeaturePair",
    "PopularityFeatureResult",
    "build_gold",
    "get_feature_coverage_report",
    "query_feature_coverage",
    "query_missing_features",
    "query_mood_segments",
    "query_movers",
    "query_popularity_feature_pairs",
    "sql_feature_coverage",
    "sql_missing_features",
    "sql_mood_segments",
    "sql_movers",
    "sql_popularity_feature_pairs",
]
