"""Gold SQL templates — load/check docs/sql/gold_queries.sql.

Runtime query builders only (not VIEW DDL). Used by gold readers.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from spotify_pipeline.pipeline.silver import sql_fact_chart_left_join_dim_track
from spotify_pipeline.state.watermark import Watermark

# docs/sql/… relative to repo root (…/pipeline/gold/sql.py → parents[4])
SQL_GOLD_QUERIES = (
    Path(__file__).resolve().parents[4] / "docs" / "sql" / "gold" / "gold_queries.sql"
)
_SQL_WHERE_PLACEHOLDER = "/*__WHERE__*/"
_SQL_BASE_JOIN_PLACEHOLDER = "/*__BASE_JOIN__*/"
_SQL_LIMIT_PLACEHOLDER = "/*__LIMIT__*/"
_QUERY_MARKER_PREFIX = "-- @@query:"

# Back-compat alias for tests that import _SQL_GOLD_QUERIES from gold.
_SQL_GOLD_QUERIES = SQL_GOLD_QUERIES


class GoldError(RuntimeError):
    """Raised when Gold SQL load or read fails."""


def sql_feature_coverage(watermark: Watermark) -> str:
    """Load coverage query from docs/sql/gold/gold_queries.sql + watermark WHERE."""
    return _sql_with_watermark_where("feature_coverage", watermark)


def sql_movers(watermark: Watermark) -> str:
    """Load movers query from docs/sql/gold/gold_queries.sql + watermark WHERE."""
    return _sql_with_watermark_where("movers", watermark)


def sql_mood_segments(watermark: Watermark) -> str:
    """Load mood query from docs/sql/gold/gold_queries.sql + watermark WHERE."""
    return _sql_with_watermark_where("mood_segments", watermark)


def sql_popularity_feature_pairs(watermark: Watermark) -> str:
    """Ad-hoc popularity vs features (GQ-4); watermark columns on alias ``f``."""
    return _sql_with_watermark_where(
        "popularity_feature_pairs", watermark, table_alias="f"
    )


def sql_missing_features(watermark: Watermark, *, top_n: int) -> str:
    """Load missing wrapper; compose Silver BR-6 LEFT JOIN as subquery."""
    template = _gold_query("missing_features")
    for placeholder in (_SQL_BASE_JOIN_PLACEHOLDER, _SQL_LIMIT_PLACEHOLDER):
        if placeholder not in template:
            raise GoldError(
                f"SQL template missing {placeholder}: {SQL_GOLD_QUERIES}"
            )
    base = sql_fact_chart_left_join_dim_track(watermark).rstrip().rstrip(";")
    return (
        template.replace(_SQL_BASE_JOIN_PLACEHOLDER, base).replace(
            _SQL_LIMIT_PLACEHOLDER, str(int(top_n))
        )
    )


def _sql_with_watermark_where(
    query_name: str,
    watermark: Watermark,
    *,
    table_alias: str = "",
) -> str:
    template = _gold_query(query_name)
    count = template.count(_SQL_WHERE_PLACEHOLDER)
    if count != 1:
        raise GoldError(
            f"SQL section {query_name!r} must contain {_SQL_WHERE_PLACEHOLDER} "
            f"exactly once (found {count}; check comments): {SQL_GOLD_QUERIES}"
        )
    prefix = f"{table_alias}." if table_alias else ""
    where = (
        f"WHERE {prefix}chart_date = CAST("
        f"{_sql_str(watermark.chart_date)} AS date)\n"
        f"  AND {prefix}chart_type = {_sql_str(watermark.chart_type)}\n"
        f"  AND {prefix}country = {_sql_str(watermark.country)}"
    )
    return template.replace(_SQL_WHERE_PLACEHOLDER, where, 1)


@lru_cache(maxsize=1)
def _load_gold_queries() -> str:
    if not SQL_GOLD_QUERIES.is_file():
        raise GoldError(f"Gold SQL file not found: {SQL_GOLD_QUERIES}")
    return SQL_GOLD_QUERIES.read_text(encoding="utf-8")


def _gold_query(name: str) -> str:
    """Extract one `-- @@query: <name>` section from gold_queries.sql."""
    marker = f"{_QUERY_MARKER_PREFIX} {name}"
    text = _load_gold_queries()
    start = text.find(marker)
    if start < 0:
        raise GoldError(f"Gold SQL missing section {marker!r}: {SQL_GOLD_QUERIES}")
    body_start = text.find("\n", start)
    if body_start < 0:
        raise GoldError(f"Gold SQL empty section {marker!r}: {SQL_GOLD_QUERIES}")
    rest = text[body_start + 1 :]
    next_marker = rest.find(f"\n{_QUERY_MARKER_PREFIX}")
    section = rest if next_marker < 0 else rest[:next_marker]
    return section.strip()


def _sql_str(value: str) -> str:
    return "'" + str(value).replace("'", "''") + "'"
