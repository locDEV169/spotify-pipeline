"""SPEC C11 — Gold readers (G1: feature coverage).

G1: query `music.gold_feature_coverage` + optional missing top-N via LEFT JOIN.
SQL templates: docs/sql/gold_queries.sql
Later: movers / mood / build_gold one-pass (G2–G6).

Gold reads Silver only — no HTTP.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from spotify_pipeline.config import get_settings
from spotify_pipeline.db.postgres import (
    PostgresConfigError,
    connect_postgres,
    require_db_url,
)
from spotify_pipeline.pipeline.silver import sql_fact_chart_left_join_dim_track
from spotify_pipeline.state.watermark import Watermark

# docs/sql/… relative to repo root (…/src/spotify_pipeline/pipeline → parents[3])
_SQL_GOLD_QUERIES = (
    Path(__file__).resolve().parents[3] / "docs" / "sql" / "gold_queries.sql"
)
_SQL_WHERE_PLACEHOLDER = "/*__WHERE__*/"
_SQL_BASE_JOIN_PLACEHOLDER = "/*__BASE_JOIN__*/"
_SQL_LIMIT_PLACEHOLDER = "/*__LIMIT__*/"
_QUERY_MARKER_PREFIX = "-- @@query:"

_DEFAULT_MISSING_TOP_N = 10


class GoldError(RuntimeError):
    """Raised when Gold read fails."""


@dataclass(frozen=True, slots=True)
class FeatureCoverageResult:
    """One watermark row from music.gold_feature_coverage."""

    watermark: tuple[str, str, str]
    chart_rows: int
    features_found_rows: int
    features_found_pct: float | None


@dataclass(frozen=True, slots=True)
class MissingFeatureRow:
    """Chart rank missing ReccoBeats features (BR-6: still on chart)."""

    rank: int
    track_id: str
    track_name: str | None
    features_found: bool | None


@dataclass(frozen=True, slots=True)
class FeatureCoverageReport:
    """Coverage aggregate + optional missing top-N ranks."""

    coverage: FeatureCoverageResult | None
    missing: list[MissingFeatureRow]


def query_feature_coverage(
    watermark: Watermark,
    *,
    conn: Any | None = None,
) -> FeatureCoverageResult | None:
    """Read music.gold_feature_coverage for one watermark; None if no VIEW row."""
    settings = get_settings()
    try:
        require_db_url(settings)
    except PostgresConfigError as exc:
        raise GoldError(str(exc)) from exc

    db_url = settings.supabase_db_url.strip()
    owns = conn is None
    db = conn or connect_postgres(db_url)
    try:
        rows = db.run(sql_feature_coverage(watermark))
        if not rows:
            return None
        row = rows[0]
        pct = row[5]
        return FeatureCoverageResult(
            watermark=(
                str(row[0]),
                str(row[1]),
                str(row[2]),
            ),
            chart_rows=int(row[3]),
            features_found_rows=int(row[4]),
            features_found_pct=float(pct) if pct is not None else None,
        )
    finally:
        if owns:
            db.close()


def query_missing_features(
    watermark: Watermark,
    *,
    top_n: int = _DEFAULT_MISSING_TOP_N,
    conn: Any | None = None,
) -> list[MissingFeatureRow]:
    """Missing top-N ranks: fact LEFT JOIN dim where features_found IS NOT TRUE."""
    if top_n < 1:
        raise GoldError(f"top_n must be >= 1, got {top_n}")

    settings = get_settings()
    try:
        require_db_url(settings)
    except PostgresConfigError as exc:
        raise GoldError(str(exc)) from exc

    db_url = settings.supabase_db_url.strip()
    owns = conn is None
    db = conn or connect_postgres(db_url)
    try:
        rows = db.run(sql_missing_features(watermark, top_n=top_n))
        out: list[MissingFeatureRow] = []
        for rank, track_id, track_name, features_found in rows or []:
            out.append(
                MissingFeatureRow(
                    rank=int(rank),
                    track_id=str(track_id),
                    track_name=str(track_name) if track_name is not None else None,
                    features_found=(
                        bool(features_found) if features_found is not None else None
                    ),
                )
            )
        return out
    finally:
        if owns:
            db.close()


def get_feature_coverage_report(
    watermark: Watermark,
    *,
    missing_top_n: int | None = _DEFAULT_MISSING_TOP_N,
    conn: Any | None = None,
) -> FeatureCoverageReport:
    """Coverage VIEW row + optional missing top-N (G1 report)."""
    settings = get_settings()
    try:
        require_db_url(settings)
    except PostgresConfigError as exc:
        raise GoldError(str(exc)) from exc

    db_url = settings.supabase_db_url.strip()
    owns = conn is None
    db = conn or connect_postgres(db_url)
    try:
        coverage = query_feature_coverage(watermark, conn=db)
        missing: list[MissingFeatureRow] = []
        if missing_top_n is not None:
            missing = query_missing_features(
                watermark, top_n=missing_top_n, conn=db
            )
        return FeatureCoverageReport(coverage=coverage, missing=missing)
    finally:
        if owns:
            db.close()


def sql_feature_coverage(watermark: Watermark) -> str:
    """Load coverage query from docs/sql/gold_queries.sql + watermark WHERE."""
    template = _gold_query("feature_coverage")
    if _SQL_WHERE_PLACEHOLDER not in template:
        raise GoldError(
            f"SQL template missing {_SQL_WHERE_PLACEHOLDER}: {_SQL_GOLD_QUERIES}"
        )
    where = (
        "WHERE chart_date = CAST("
        f"{_sql_str(watermark.chart_date)} AS date)\n"
        f"  AND chart_type = {_sql_str(watermark.chart_type)}\n"
        f"  AND country = {_sql_str(watermark.country)}"
    )
    return template.replace(_SQL_WHERE_PLACEHOLDER, where)


def sql_missing_features(watermark: Watermark, *, top_n: int) -> str:
    """Load missing wrapper; compose Silver BR-6 LEFT JOIN as subquery."""
    template = _gold_query("missing_features")
    for placeholder in (_SQL_BASE_JOIN_PLACEHOLDER, _SQL_LIMIT_PLACEHOLDER):
        if placeholder not in template:
            raise GoldError(
                f"SQL template missing {placeholder}: {_SQL_GOLD_QUERIES}"
            )
    base = sql_fact_chart_left_join_dim_track(watermark).rstrip().rstrip(";")
    return (
        template.replace(_SQL_BASE_JOIN_PLACEHOLDER, base).replace(
            _SQL_LIMIT_PLACEHOLDER, str(int(top_n))
        )
    )


@lru_cache(maxsize=1)
def _load_gold_queries() -> str:
    if not _SQL_GOLD_QUERIES.is_file():
        raise GoldError(f"Gold SQL file not found: {_SQL_GOLD_QUERIES}")
    return _SQL_GOLD_QUERIES.read_text(encoding="utf-8")


def _gold_query(name: str) -> str:
    """Extract one `-- @@query: <name>` section from gold_queries.sql."""
    marker = f"{_QUERY_MARKER_PREFIX} {name}"
    text = _load_gold_queries()
    start = text.find(marker)
    if start < 0:
        raise GoldError(f"Gold SQL missing section {marker!r}: {_SQL_GOLD_QUERIES}")
    body_start = text.find("\n", start)
    if body_start < 0:
        raise GoldError(f"Gold SQL empty section {marker!r}: {_SQL_GOLD_QUERIES}")
    rest = text[body_start + 1 :]
    next_marker = rest.find(f"\n{_QUERY_MARKER_PREFIX}")
    section = rest if next_marker < 0 else rest[:next_marker]
    return section.strip()


def _sql_str(value: str) -> str:
    return "'" + str(value).replace("'", "''") + "'"
