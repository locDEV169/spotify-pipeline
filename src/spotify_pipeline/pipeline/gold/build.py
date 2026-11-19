"""SPEC C11 — Gold one-pass orchestrator (G6).

G5 (GQ-5 Answer): formal SCD2 table **deferred**. Diagram may show SCD2;
DDL has none. MVP rank history = append-only `fact_chart` / movers VIEW only
— no `valid_from`/`valid_to` table until Chubby promotes GQ-5.

Does not wire into `run` (GQ-8). Reads Silver only — no HTTP.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from spotify_pipeline.config import get_settings
from spotify_pipeline.db.postgres import (
    PostgresConfigError,
    connect_postgres,
    require_db_url,
)
from spotify_pipeline.pipeline.gold.readers import (
    FeatureCoverageResult,
    get_feature_coverage_report,
    query_mood_segments,
    query_movers,
    query_popularity_feature_pairs,
)
from spotify_pipeline.pipeline.gold.sql import GoldError
from spotify_pipeline.state.watermark import Watermark

# GQ-5 locked for this MVP: defer formal SCD2 DDL.
SCD2_STATUS = "deferred"


@dataclass(frozen=True, slots=True)
class GoldBuildResult:
    """Summary of one watermark Gold read (G1–G4; G5 deferred)."""

    watermark: tuple[str, str, str]
    coverage: FeatureCoverageResult | None
    missing_count: int
    movers_count: int
    mood_count: int
    popularity_skipped: bool
    popularity_pairs: int
    popularity_reason: str | None
    scd2_status: str = SCD2_STATUS


def build_gold(
    watermark: Watermark,
    *,
    missing_top_n: int | None = 10,
    conn: Any | None = None,
) -> GoldBuildResult:
    """G6 one-pass: coverage (+ missing) → movers → mood → popularity skip-safe."""
    settings = get_settings()
    try:
        require_db_url(settings)
    except PostgresConfigError as exc:
        raise GoldError(str(exc)) from exc

    db_url = settings.supabase_db_url.strip()
    owns = conn is None
    db = conn or connect_postgres(db_url)
    try:
        report = get_feature_coverage_report(
            watermark, missing_top_n=missing_top_n, conn=db
        )
        movers = query_movers(watermark, conn=db)
        mood = query_mood_segments(watermark, conn=db)
        popularity = query_popularity_feature_pairs(watermark, conn=db)
        return GoldBuildResult(
            watermark=watermark.as_tuple(),
            coverage=report.coverage,
            missing_count=len(report.missing),
            movers_count=len(movers),
            mood_count=len(mood),
            popularity_skipped=popularity.skipped,
            popularity_pairs=len(popularity.rows),
            popularity_reason=popularity.reason,
            scd2_status=SCD2_STATUS,
        )
    finally:
        if owns:
            db.close()
