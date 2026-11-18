"""SPEC C10 — Silver builders.

W1: fact_chart · W2: dim_track metadata · W3: dim_artist + bridge · W4: features_found.
W5: LEFT JOIN read path + COALESCE upsert semantics · W6: one-pass `build_silver`.

Silver reads only `music.raw_*` — no HTTP.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

# docs/sql/… relative to repo root (…/src/spotify_pipeline/pipeline → parents[3])
_SQL_FACT_LEFT_JOIN = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "sql"
    / "silver_fact_chart_left_join_dim_track.sql"
)
_SQL_WHERE_PLACEHOLDER = "/*__WHERE__*/"

from spotify_pipeline.config import get_settings
from spotify_pipeline.db.postgres import (
    PostgresConfigError,
    connect_postgres,
    require_db_url,
)
from spotify_pipeline.models.audio_features import (
    AudioFeatures,
    AudioFeaturesModelError,
    audio_features_from_reccobeats_item,
)
from spotify_pipeline.models.chart import (
    ChartEntry,
    ChartModelError,
    chart_entries_from_view,
)
from spotify_pipeline.models.track import (
    ArtistMetadata,
    TrackArtistLink,
    TrackMetadata,
    TrackModelError,
    artist_from_spotify_payload,
    bridge_links_from_track_payload,
    track_from_spotify_payload,
)
from spotify_pipeline.pipeline.extract_ids import (
    ExtractIdsError,
    fetch_latest_raw_charts_payload,
    ids_from_bronze_payload,
)
from spotify_pipeline.state.watermark import Watermark

_SOURCE_CHARTS = "charts_public_v0"
_SOURCE_SPOTIFY = "spotify_web_api"
_SOURCE_RECCOBEATS = "reccobeats"
_SUPPORTED_CHART_TYPES = frozenset({"weekly_top_songs"})


class SilverError(RuntimeError):
    """Raised when Silver build fails."""


@dataclass(frozen=True, slots=True)
class FactChartBuildResult:
    """Summary of a W1 fact_chart build for one watermark."""

    watermark: tuple[str, str, str]
    raw_charts_id: int | None
    upserted: int
    run_id: str


@dataclass(frozen=True, slots=True)
class DimTrackBuildResult:
    """Summary of a W2 dim_track metadata build for one watermark."""

    watermark: tuple[str, str, str]
    track_ids: int
    upserted: int
    missed: int
    run_id: str


@dataclass(frozen=True, slots=True)
class ArtistBridgeBuildResult:
    """Summary of a W3 dim_artist + bridge build for one watermark."""

    watermark: tuple[str, str, str]
    artists_upserted: int
    bridges_upserted: int
    artists_missed: int
    run_id: str


@dataclass(frozen=True, slots=True)
class FeaturesBuildResult:
    """Summary of a W4 ReccoBeats features_found build for one watermark."""

    watermark: tuple[str, str, str]
    track_ids: int
    hits: int
    misses: int
    run_id: str


@dataclass(frozen=True, slots=True)
class SilverBuildResult:
    """W6 one-pass summary: fact → dims → bridge → features."""

    watermark: tuple[str, str, str]
    run_id: str
    fact: FactChartBuildResult
    dim_track: DimTrackBuildResult
    artist_bridge: ArtistBridgeBuildResult
    features: FeaturesBuildResult


def fact_entries_from_bronze_payload(payload: dict[str, Any]) -> list[ChartEntry]:
    """Parse ChartEntry rows from a Bronze charts payload (public/v0)."""
    try:
        return chart_entries_from_view(payload)
    except ChartModelError as exc:
        raise SilverError(str(exc)) from exc


def upsert_fact_chart_rows(
    conn: Any,
    watermark: Watermark,
    entries: list[ChartEntry],
    *,
    run_id: str,
    source: str = _SOURCE_CHARTS,
) -> int:
    """Upsert fact_chart rows; returns number of statements executed."""
    if not entries:
        raise SilverError("no ChartEntry rows to upsert into fact_chart")

    for entry in entries:
        sql = f"""
            INSERT INTO music.fact_chart (
                chart_date, chart_type, country, track_id,
                rank, prev_rank, streams, entry_status,
                run_id, source, ingested_at
            ) VALUES (
                CAST({_sql_str(watermark.chart_date)} AS date),
                {_sql_str(watermark.chart_type)},
                {_sql_str(watermark.country)},
                {_sql_str(entry.track_id)},
                {int(entry.rank)},
                {_sql_int_or_null(entry.prev_rank)},
                {_sql_int_or_null(entry.streams)},
                {_sql_str_or_null(entry.entry_status)},
                {_sql_str(run_id)},
                {_sql_str(source)},
                now()
            )
            ON CONFLICT (chart_date, chart_type, country, track_id) DO UPDATE SET
                rank         = EXCLUDED.rank,
                prev_rank    = EXCLUDED.prev_rank,
                streams      = EXCLUDED.streams,
                entry_status = EXCLUDED.entry_status,
                run_id       = EXCLUDED.run_id,
                source       = EXCLUDED.source,
                ingested_at  = EXCLUDED.ingested_at
            """
        conn.run(sql)
    return len(entries)


def build_fact_chart(
    watermark: Watermark,
    *,
    conn: Any | None = None,
    run_id: str | None = None,
) -> FactChartBuildResult:
    """W1: latest raw_charts for watermark → upsert music.fact_chart."""
    if watermark.chart_type not in _SUPPORTED_CHART_TYPES:
        raise SilverError(
            f"unsupported chart_type for fact_chart: {watermark.chart_type!r}; "
            f"expected one of {sorted(_SUPPORTED_CHART_TYPES)}"
        )

    settings = get_settings()
    try:
        require_db_url(settings)
    except PostgresConfigError as exc:
        raise SilverError(str(exc)) from exc

    db_url = settings.supabase_db_url.strip()
    rid = run_id or uuid.uuid4().hex
    owns = conn is None
    db = conn or connect_postgres(db_url)
    try:
        try:
            raw_id, payload = fetch_latest_raw_charts_payload(db, watermark)
        except ExtractIdsError as exc:
            raise SilverError(str(exc)) from exc
        entries = fact_entries_from_bronze_payload(payload)
        upserted = upsert_fact_chart_rows(db, watermark, entries, run_id=rid)
        return FactChartBuildResult(
            watermark=watermark.as_tuple(),
            raw_charts_id=raw_id,
            upserted=upserted,
            run_id=rid,
        )
    finally:
        if owns:
            db.close()


def fetch_latest_raw_spotify(
    conn: Any,
    spotify_ids: list[str],
    *,
    entity: str,
) -> dict[str, dict[str, Any]]:
    """SQ-3: latest raw_spotify row per spotify_id for entity track|artist."""
    if not spotify_ids:
        return {}
    id_list = ", ".join(_sql_str(sid) for sid in spotify_ids)
    sql = f"""
        SELECT DISTINCT ON (spotify_id) spotify_id, payload
        FROM music.raw_spotify
        WHERE entity = {_sql_str(entity)}
          AND spotify_id IN ({id_list})
        ORDER BY spotify_id, ingested_at DESC
        """
    rows = conn.run(sql)
    out: dict[str, dict[str, Any]] = {}
    for spotify_id, payload in rows or []:
        if isinstance(payload, str):
            payload = json.loads(payload)
        if not isinstance(payload, dict):
            raise SilverError(
                f"raw_spotify.payload for {spotify_id!r} is not a JSON object"
            )
        out[str(spotify_id)] = payload
    return out


def fetch_latest_raw_spotify_tracks(
    conn: Any,
    track_ids: list[str],
) -> dict[str, dict[str, Any]]:
    """SQ-3 helper: latest raw_spotify track payloads."""
    return fetch_latest_raw_spotify(conn, track_ids, entity="track")


def upsert_dim_track_metadata_rows(
    conn: Any,
    tracks: list[TrackMetadata],
    *,
    run_id: str,
    source: str = _SOURCE_SPOTIFY,
) -> int:
    """Upsert dim_track metadata only; does not write/wipe feature columns."""
    if not tracks:
        raise SilverError("no TrackMetadata rows to upsert into dim_track")

    for track in tracks:
        sql = f"""
            INSERT INTO music.dim_track (
                track_id, track_name, duration_ms, explicit,
                album_id, album_name, release_date, release_date_precision,
                isrc, track_popularity,
                run_id, source, updated_at
            ) VALUES (
                {_sql_str(track.track_id)},
                {_sql_str_or_null(track.track_name)},
                {_sql_int_or_null(track.duration_ms)},
                {_sql_bool_or_null(track.explicit)},
                {_sql_str_or_null(track.album_id)},
                {_sql_str_or_null(track.album_name)},
                {_sql_str_or_null(track.release_date)},
                {_sql_str_or_null(track.release_date_precision)},
                {_sql_str_or_null(track.isrc)},
                {_sql_int_or_null(track.track_popularity)},
                {_sql_str(run_id)},
                {_sql_str(source)},
                now()
            )
            ON CONFLICT (track_id) DO UPDATE SET
                track_name               = EXCLUDED.track_name,
                duration_ms              = EXCLUDED.duration_ms,
                explicit                 = EXCLUDED.explicit,
                album_id                 = EXCLUDED.album_id,
                album_name               = EXCLUDED.album_name,
                release_date             = EXCLUDED.release_date,
                release_date_precision   = EXCLUDED.release_date_precision,
                isrc                     = COALESCE(EXCLUDED.isrc, dim_track.isrc),
                track_popularity         = EXCLUDED.track_popularity,
                run_id                   = EXCLUDED.run_id,
                source                   = EXCLUDED.source,
                updated_at               = EXCLUDED.updated_at
            """
        conn.run(sql)
    return len(tracks)


def build_dim_track(
    watermark: Watermark,
    *,
    conn: Any | None = None,
    run_id: str | None = None,
    track_ids: list[str] | None = None,
) -> DimTrackBuildResult:
    """W2: watermark track IDs → latest raw_spotify track → upsert dim_track."""
    if watermark.chart_type not in _SUPPORTED_CHART_TYPES:
        raise SilverError(
            f"unsupported chart_type for dim_track: {watermark.chart_type!r}; "
            f"expected one of {sorted(_SUPPORTED_CHART_TYPES)}"
        )

    settings = get_settings()
    try:
        require_db_url(settings)
    except PostgresConfigError as exc:
        raise SilverError(str(exc)) from exc

    db_url = settings.supabase_db_url.strip()
    rid = run_id or uuid.uuid4().hex
    owns = conn is None
    db = conn or connect_postgres(db_url)
    try:
        ids = list(track_ids) if track_ids is not None else None
        if ids is None:
            try:
                _, payload = fetch_latest_raw_charts_payload(db, watermark)
                extracted = ids_from_bronze_payload(watermark, payload)
                ids = list(extracted.track_ids)
            except ExtractIdsError as exc:
                raise SilverError(str(exc)) from exc
        if not ids:
            raise SilverError("no track ids for dim_track build")

        payloads = fetch_latest_raw_spotify_tracks(db, ids)
        tracks: list[TrackMetadata] = []
        missed = 0
        for tid in ids:
            raw = payloads.get(tid)
            if raw is None:
                missed += 1
                continue
            try:
                tracks.append(track_from_spotify_payload(raw, spotify_id=tid))
            except TrackModelError as exc:
                raise SilverError(str(exc)) from exc

        if not tracks:
            raise SilverError(
                "no Bronze raw_spotify track rows for watermark track set; "
                "run enrich-spotify first"
            )

        upserted = upsert_dim_track_metadata_rows(db, tracks, run_id=rid)
        return DimTrackBuildResult(
            watermark=watermark.as_tuple(),
            track_ids=len(ids),
            upserted=upserted,
            missed=missed,
            run_id=rid,
        )
    finally:
        if owns:
            db.close()


def upsert_dim_artist_rows(
    conn: Any,
    artists: list[ArtistMetadata],
    *,
    run_id: str,
    source: str = _SOURCE_SPOTIFY,
) -> int:
    """Upsert music.dim_artist rows."""
    if not artists:
        raise SilverError("no ArtistMetadata rows to upsert into dim_artist")

    for artist in artists:
        genres_sql = (
            "NULL" if artist.genres is None else _sql_jsonb(artist.genres)
        )
        sql = f"""
            INSERT INTO music.dim_artist (
                artist_id, artist_name, genres, followers, artist_popularity,
                run_id, source, updated_at
            ) VALUES (
                {_sql_str(artist.artist_id)},
                {_sql_str_or_null(artist.artist_name)},
                {genres_sql},
                {_sql_int_or_null(artist.followers)},
                {_sql_int_or_null(artist.artist_popularity)},
                {_sql_str(run_id)},
                {_sql_str(source)},
                now()
            )
            ON CONFLICT (artist_id) DO UPDATE SET
                artist_name         = EXCLUDED.artist_name,
                genres              = EXCLUDED.genres,
                followers           = EXCLUDED.followers,
                artist_popularity   = EXCLUDED.artist_popularity,
                run_id              = EXCLUDED.run_id,
                source              = EXCLUDED.source,
                updated_at          = EXCLUDED.updated_at
            """
        conn.run(sql)
    return len(artists)


def upsert_bridge_track_artist_rows(
    conn: Any,
    links: list[TrackArtistLink],
) -> int:
    """Upsert bridge_track_artist (PK track_id+artist_id); positions 0-based."""
    if not links:
        return 0
    for link in links:
        sql = f"""
            INSERT INTO music.bridge_track_artist (
                track_id, artist_id, artist_position
            ) VALUES (
                {_sql_str(link.track_id)},
                {_sql_str(link.artist_id)},
                {int(link.artist_position)}
            )
            ON CONFLICT (track_id, artist_id) DO UPDATE SET
                artist_position = EXCLUDED.artist_position
            """
        conn.run(sql)
    return len(links)


def build_dim_artist_bridge(
    watermark: Watermark,
    *,
    conn: Any | None = None,
    run_id: str | None = None,
    track_ids: list[str] | None = None,
) -> ArtistBridgeBuildResult:
    """W3: track.artists + raw_spotify artists → dim_artist + bridge."""
    if watermark.chart_type not in _SUPPORTED_CHART_TYPES:
        raise SilverError(
            f"unsupported chart_type for artist/bridge: {watermark.chart_type!r}; "
            f"expected one of {sorted(_SUPPORTED_CHART_TYPES)}"
        )

    settings = get_settings()
    try:
        require_db_url(settings)
    except PostgresConfigError as exc:
        raise SilverError(str(exc)) from exc

    db_url = settings.supabase_db_url.strip()
    rid = run_id or uuid.uuid4().hex
    owns = conn is None
    db = conn or connect_postgres(db_url)
    try:
        ids = _resolve_track_ids(db, watermark, track_ids)
        track_payloads = fetch_latest_raw_spotify_tracks(db, ids)
        links: list[TrackArtistLink] = []
        for tid in ids:
            raw = track_payloads.get(tid)
            if raw is None:
                continue
            try:
                links.extend(
                    bridge_links_from_track_payload(raw, track_id=tid)
                )
            except TrackModelError as exc:
                raise SilverError(str(exc)) from exc

        if not links:
            raise SilverError(
                "no track.artists links for watermark; run enrich-spotify first"
            )

        artist_ids = list(dict.fromkeys(link.artist_id for link in links))
        artist_payloads = fetch_latest_raw_spotify(db, artist_ids, entity="artist")
        artists: list[ArtistMetadata] = []
        missed = 0
        embedded_name = {link.artist_id: link.artist_name for link in links}
        for aid in artist_ids:
            raw = artist_payloads.get(aid)
            if raw is not None:
                try:
                    artists.append(
                        artist_from_spotify_payload(raw, spotify_id=aid)
                    )
                except TrackModelError as exc:
                    raise SilverError(str(exc)) from exc
            else:
                # Bronze artist miss: still upsert id+name from track.artists embed.
                missed += 1
                artists.append(
                    ArtistMetadata(
                        artist_id=aid,
                        artist_name=embedded_name.get(aid),
                        genres=None,
                        followers=None,
                        artist_popularity=None,
                    )
                )

        artists_upserted = upsert_dim_artist_rows(db, artists, run_id=rid)
        bridges_upserted = upsert_bridge_track_artist_rows(db, links)
        return ArtistBridgeBuildResult(
            watermark=watermark.as_tuple(),
            artists_upserted=artists_upserted,
            bridges_upserted=bridges_upserted,
            artists_missed=missed,
            run_id=rid,
        )
    finally:
        if owns:
            db.close()


def fetch_reccobeats_features_by_track_id(
    conn: Any,
    track_ids: list[str],
) -> dict[str, AudioFeatures]:
    """Latest ReccoBeats content[] hits keyed by Spotify track id (via href)."""
    if not track_ids:
        return {}
    id_list = ", ".join(_sql_str(tid) for tid in track_ids)
    sql = f"""
        SELECT payload
        FROM music.raw_reccobeats
        WHERE endpoint = 'audio-features'
          AND spotify_track_ids && ARRAY[{id_list}]::text[]
        ORDER BY ingested_at DESC
        """
    rows = conn.run(sql)
    found: dict[str, AudioFeatures] = {}
    wanted = set(track_ids)
    for (payload,) in rows or []:
        if isinstance(payload, str):
            payload = json.loads(payload)
        if not isinstance(payload, dict):
            continue
        content = payload.get("content") or []
        if not isinstance(content, list):
            continue
        for item in content:
            if not isinstance(item, dict):
                continue
            try:
                features = audio_features_from_reccobeats_item(item)
            except AudioFeaturesModelError:
                continue
            if features.track_id not in wanted or features.track_id in found:
                continue
            found[features.track_id] = features
        if len(found) >= len(wanted):
            break
    return found


def upsert_dim_track_features_rows(
    conn: Any,
    features: list[AudioFeatures],
    *,
    run_id: str,
    source: str = _SOURCE_RECCOBEATS,
) -> int:
    """Upsert ReccoBeats feature cols; COALESCE preserves existing metadata."""
    if not features:
        return 0
    for feat in features:
        sql = f"""
            INSERT INTO music.dim_track (
                track_id,
                reccobeats_uuid, href,
                acousticness, danceability, energy, instrumentalness,
                liveness, speechiness, valence, loudness, tempo, key, mode,
                features_found, features_fetched_at, source_features,
                run_id, source, updated_at
            ) VALUES (
                {_sql_str(feat.track_id)},
                {_sql_str_or_null(feat.reccobeats_uuid)},
                {_sql_str_or_null(feat.href)},
                {_sql_float_or_null(feat.acousticness)},
                {_sql_float_or_null(feat.danceability)},
                {_sql_float_or_null(feat.energy)},
                {_sql_float_or_null(feat.instrumentalness)},
                {_sql_float_or_null(feat.liveness)},
                {_sql_float_or_null(feat.speechiness)},
                {_sql_float_or_null(feat.valence)},
                {_sql_float_or_null(feat.loudness)},
                {_sql_float_or_null(feat.tempo)},
                {_sql_int_or_null(feat.key)},
                {_sql_int_or_null(feat.mode)},
                TRUE,
                now(),
                {_sql_str(source)},
                {_sql_str(run_id)},
                {_sql_str(source)},
                now()
            )
            ON CONFLICT (track_id) DO UPDATE SET
                reccobeats_uuid     = COALESCE(EXCLUDED.reccobeats_uuid, dim_track.reccobeats_uuid),
                href                = COALESCE(EXCLUDED.href, dim_track.href),
                acousticness        = COALESCE(EXCLUDED.acousticness, dim_track.acousticness),
                danceability        = COALESCE(EXCLUDED.danceability, dim_track.danceability),
                energy              = COALESCE(EXCLUDED.energy, dim_track.energy),
                instrumentalness    = COALESCE(EXCLUDED.instrumentalness, dim_track.instrumentalness),
                liveness            = COALESCE(EXCLUDED.liveness, dim_track.liveness),
                speechiness         = COALESCE(EXCLUDED.speechiness, dim_track.speechiness),
                valence             = COALESCE(EXCLUDED.valence, dim_track.valence),
                loudness            = COALESCE(EXCLUDED.loudness, dim_track.loudness),
                tempo               = COALESCE(EXCLUDED.tempo, dim_track.tempo),
                key                 = COALESCE(EXCLUDED.key, dim_track.key),
                mode                = COALESCE(EXCLUDED.mode, dim_track.mode),
                features_found      = EXCLUDED.features_found,
                features_fetched_at = COALESCE(EXCLUDED.features_fetched_at, dim_track.features_fetched_at),
                source_features     = COALESCE(EXCLUDED.source_features, dim_track.source_features),
                run_id              = EXCLUDED.run_id,
                updated_at          = EXCLUDED.updated_at
            """
        conn.run(sql)
    return len(features)


def mark_dim_track_features_misses(
    conn: Any,
    track_ids: list[str],
    *,
    run_id: str,
) -> int:
    """Set features_found=false for misses; never deletes fact_chart."""
    if not track_ids:
        return 0
    n = 0
    for tid in track_ids:
        sql = f"""
            UPDATE music.dim_track
            SET features_found = FALSE,
                run_id = {_sql_str(run_id)},
                updated_at = now()
            WHERE track_id = {_sql_str(tid)}
            """
        conn.run(sql)
        n += 1
    return n


def build_dim_track_features(
    watermark: Watermark,
    *,
    conn: Any | None = None,
    run_id: str | None = None,
    track_ids: list[str] | None = None,
) -> FeaturesBuildResult:
    """W4: raw_reccobeats → features_found true/false on dim_track."""
    if watermark.chart_type not in _SUPPORTED_CHART_TYPES:
        raise SilverError(
            f"unsupported chart_type for features: {watermark.chart_type!r}; "
            f"expected one of {sorted(_SUPPORTED_CHART_TYPES)}"
        )

    settings = get_settings()
    try:
        require_db_url(settings)
    except PostgresConfigError as exc:
        raise SilverError(str(exc)) from exc

    db_url = settings.supabase_db_url.strip()
    rid = run_id or uuid.uuid4().hex
    owns = conn is None
    db = conn or connect_postgres(db_url)
    try:
        ids = _resolve_track_ids(db, watermark, track_ids)
        found = fetch_reccobeats_features_by_track_id(db, ids)
        hits = [found[tid] for tid in ids if tid in found]
        misses = [tid for tid in ids if tid not in found]
        upsert_dim_track_features_rows(db, hits, run_id=rid)
        mark_dim_track_features_misses(db, misses, run_id=rid)
        return FeaturesBuildResult(
            watermark=watermark.as_tuple(),
            track_ids=len(ids),
            hits=len(hits),
            misses=len(misses),
            run_id=rid,
        )
    finally:
        if owns:
            db.close()


@lru_cache(maxsize=1)
def _load_fact_chart_left_join_sql() -> str:
    return _SQL_FACT_LEFT_JOIN.read_text(encoding="utf-8")


def sql_fact_chart_left_join_dim_track(watermark: Watermark | None = None) -> str:
    """BR-6 read path: load docs/sql/silver_fact_chart_left_join_dim_track.sql.

    Optional watermark injects WHERE; chart rows still survive missing dim/features.
    """
    where = ""
    if watermark is not None:
        where = (
            "WHERE f.chart_date = CAST("
            f"{_sql_str(watermark.chart_date)} AS date)\n"
            f"  AND f.chart_type = {_sql_str(watermark.chart_type)}\n"
            f"  AND f.country = {_sql_str(watermark.country)}"
        )
    template = _load_fact_chart_left_join_sql()
    if _SQL_WHERE_PLACEHOLDER not in template:
        raise SilverError(
            f"SQL template missing {_SQL_WHERE_PLACEHOLDER}: {_SQL_FACT_LEFT_JOIN}"
        )
    return template.replace(_SQL_WHERE_PLACEHOLDER, where)


def build_silver(
    watermark: Watermark,
    *,
    conn: Any | None = None,
    run_id: str | None = None,
) -> SilverBuildResult:
    """W6 one-pass: fact → dim_track → artist/bridge → features (shared run_id)."""
    if watermark.chart_type not in _SUPPORTED_CHART_TYPES:
        raise SilverError(
            f"unsupported chart_type for build_silver: {watermark.chart_type!r}; "
            f"expected one of {sorted(_SUPPORTED_CHART_TYPES)}"
        )

    settings = get_settings()
    try:
        require_db_url(settings)
    except PostgresConfigError as exc:
        raise SilverError(str(exc)) from exc

    db_url = settings.supabase_db_url.strip()
    rid = run_id or uuid.uuid4().hex
    owns = conn is None
    db = conn or connect_postgres(db_url)
    try:
        fact = build_fact_chart(watermark, conn=db, run_id=rid)
        dim = build_dim_track(watermark, conn=db, run_id=rid)
        artists = build_dim_artist_bridge(watermark, conn=db, run_id=rid)
        features = build_dim_track_features(watermark, conn=db, run_id=rid)
        return SilverBuildResult(
            watermark=watermark.as_tuple(),
            run_id=rid,
            fact=fact,
            dim_track=dim,
            artist_bridge=artists,
            features=features,
        )
    finally:
        if owns:
            db.close()


def _resolve_track_ids(
    conn: Any,
    watermark: Watermark,
    track_ids: list[str] | None,
) -> list[str]:
    if track_ids is not None:
        ids = list(track_ids)
    else:
        try:
            _, payload = fetch_latest_raw_charts_payload(conn, watermark)
            extracted = ids_from_bronze_payload(watermark, payload)
            ids = list(extracted.track_ids)
        except ExtractIdsError as exc:
            raise SilverError(str(exc)) from exc
    if not ids:
        raise SilverError("no track ids for silver build")
    return ids


def _sql_str(value: str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _sql_str_or_null(value: str | None) -> str:
    return "NULL" if value is None else _sql_str(value)


def _sql_int_or_null(value: int | None) -> str:
    return "NULL" if value is None else str(int(value))


def _sql_float_or_null(value: float | None) -> str:
    return "NULL" if value is None else repr(float(value))


def _sql_bool_or_null(value: bool | None) -> str:
    if value is None:
        return "NULL"
    return "TRUE" if value else "FALSE"


def _sql_jsonb(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False)
    tag = "j"
    while f"${tag}$" in raw:
        tag += "x"
    return f"${tag}${raw}${tag}$::jsonb"
