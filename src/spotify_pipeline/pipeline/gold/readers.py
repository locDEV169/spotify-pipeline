"""SPEC C11 — Gold readers (G1–G4).

Gold reads Silver only — no HTTP. SQL builders live in `.sql`.

G3 mood uses VIEW INNER JOIN + features_found IS TRUE — intentional filter,
not a BR-6 chart-row drop (coverage/missing remain LEFT JOIN).

G4 popularity vs features is optional (GQ-4 / Open Q2): skip when
track_popularity absent — never invent values, never fail Gold solely for that.
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
from spotify_pipeline.pipeline.gold.sql import (
    GoldError,
    sql_feature_coverage,
    sql_missing_features,
    sql_mood_segments,
    sql_movers,
    sql_popularity_feature_pairs,
)
from spotify_pipeline.state.watermark import Watermark

_DEFAULT_MISSING_TOP_N = 10

# GQ-3 Assumption (not locked Fact): energy×valence cutovers at 0.5.
# High side uses >= 0.5. Labels: energetic | tense | chill | sad | unknown.
_MOOD_CUTOVER = 0.5

# GQ-4 / Open Q2: current Dev Mode often has all-null track_popularity.
_SKIP_NO_POPULARITY_PAIRS = (
    "no_non_null_track_popularity_or_features"
)


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


@dataclass(frozen=True, slots=True)
class MoverRow:
    """One gold_movers row. streams is display-only when NOT NULL (GQ-9 / public/v0)."""

    track_id: str
    track_name: str | None
    rank: int
    prev_rank: int
    rank_delta: int
    streams: int | None


@dataclass(frozen=True, slots=True)
class MoodRow:
    """One gold_mood_segments row + Python mood label (GQ-3 Assumption)."""

    track_id: str
    track_name: str | None
    energy: float | None
    valence: float | None
    tempo: float | None
    source_features: str | None
    mood: str


@dataclass(frozen=True, slots=True)
class PopularityFeaturePair:
    """One popularity vs features pair (only when track_popularity is present)."""

    rank: int
    track_id: str
    track_name: str | None
    track_popularity: int
    energy: float | None
    valence: float | None
    danceability: float | None


@dataclass(frozen=True, slots=True)
class PopularityFeatureResult:
    """G4 result: pairs or null-safe skip (Open Q2 / GQ-4)."""

    rows: list[PopularityFeaturePair]
    skipped: bool
    reason: str | None


def _mood_label(energy: float | None, valence: float | None) -> str:
    """Map energy×valence to a quadrant label.

    GQ-3 Assumption cutover = 0.5 (high = >= cutover):
      energetic = high energy + high valence
      tense     = high energy + low valence
      chill     = low energy  + high valence
      sad       = low energy  + low valence
      unknown   = energy or valence is NULL (features_found=true but incomplete)
    """
    if energy is None or valence is None:
        return "unknown"
    high_e = energy >= _MOOD_CUTOVER
    high_v = valence >= _MOOD_CUTOVER
    if high_e and high_v:
        return "energetic"
    if high_e and not high_v:
        return "tense"
    if not high_e and high_v:
        return "chill"
    return "sad"


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


def query_movers(
    watermark: Watermark,
    *,
    conn: Any | None = None,
) -> list[MoverRow]:
    """Read music.gold_movers for watermark; empty list if none.

    VIEW excludes prev_rank IS NULL (GQ-2). streams may be NULL (GQ-9).
    """
    settings = get_settings()
    try:
        require_db_url(settings)
    except PostgresConfigError as exc:
        raise GoldError(str(exc)) from exc

    db_url = settings.supabase_db_url.strip()
    owns = conn is None
    db = conn or connect_postgres(db_url)
    try:
        rows = db.run(sql_movers(watermark))
        out: list[MoverRow] = []
        for (
            _chart_date,
            _chart_type,
            _country,
            track_id,
            track_name,
            rank,
            prev_rank,
            rank_delta,
            streams,
        ) in rows or []:
            out.append(
                MoverRow(
                    track_id=str(track_id),
                    track_name=(
                        str(track_name) if track_name is not None else None
                    ),
                    rank=int(rank),
                    prev_rank=int(prev_rank),
                    rank_delta=int(rank_delta),
                    streams=int(streams) if streams is not None else None,
                )
            )
        return out
    finally:
        if owns:
            db.close()


def query_mood_segments(
    watermark: Watermark,
    *,
    conn: Any | None = None,
) -> list[MoodRow]:
    """Read music.gold_mood_segments for watermark; empty list if none.

    VIEW is INNER JOIN + features_found IS TRUE (≠ BR-6). Empty OK when
    coverage < 100%. Mood labels use GQ-3 Assumption 0.5 cutovers.
    """
    settings = get_settings()
    try:
        require_db_url(settings)
    except PostgresConfigError as exc:
        raise GoldError(str(exc)) from exc

    db_url = settings.supabase_db_url.strip()
    owns = conn is None
    db = conn or connect_postgres(db_url)
    try:
        rows = db.run(sql_mood_segments(watermark))
        out: list[MoodRow] = []
        for (
            _chart_date,
            _chart_type,
            _country,
            track_id,
            track_name,
            energy,
            valence,
            tempo,
            source_features,
        ) in rows or []:
            e = float(energy) if energy is not None else None
            v = float(valence) if valence is not None else None
            out.append(
                MoodRow(
                    track_id=str(track_id),
                    track_name=(
                        str(track_name) if track_name is not None else None
                    ),
                    energy=e,
                    valence=v,
                    tempo=float(tempo) if tempo is not None else None,
                    source_features=(
                        str(source_features)
                        if source_features is not None
                        else None
                    ),
                    mood=_mood_label(e, v),
                )
            )
        return out
    finally:
        if owns:
            db.close()


def query_popularity_feature_pairs(
    watermark: Watermark,
    *,
    conn: Any | None = None,
) -> PopularityFeatureResult:
    """Popularity vs energy/valence/danceability; skip if none usable (GQ-4).

    Open Q2: Dev Mode often has all-null track_popularity — skip + reason,
    do not invent values, do not fail Gold solely for that.
    """
    settings = get_settings()
    try:
        require_db_url(settings)
    except PostgresConfigError as exc:
        raise GoldError(str(exc)) from exc

    db_url = settings.supabase_db_url.strip()
    owns = conn is None
    db = conn or connect_postgres(db_url)
    try:
        raw = db.run(sql_popularity_feature_pairs(watermark))
        out: list[PopularityFeaturePair] = []
        for (
            rank,
            track_id,
            track_name,
            track_popularity,
            energy,
            valence,
            danceability,
        ) in raw or []:
            # SQL already filters NULL popularity; guard against inventing values.
            if track_popularity is None:
                continue
            out.append(
                PopularityFeaturePair(
                    rank=int(rank),
                    track_id=str(track_id),
                    track_name=(
                        str(track_name) if track_name is not None else None
                    ),
                    track_popularity=int(track_popularity),
                    energy=float(energy) if energy is not None else None,
                    valence=float(valence) if valence is not None else None,
                    danceability=(
                        float(danceability) if danceability is not None else None
                    ),
                )
            )
        if not out:
            return PopularityFeatureResult(
                rows=[],
                skipped=True,
                reason=_SKIP_NO_POPULARITY_PAIRS,
            )
        return PopularityFeatureResult(rows=out, skipped=False, reason=None)
    finally:
        if owns:
            db.close()
