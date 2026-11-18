"""SPEC C9 — Spotify track/artist enrich → Bronze (watermark-scoped)."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import httpx

from spotify_pipeline.clients.charts import (
    ALIAS_ARTISTS,
    ALIAS_SONGS,
    ChartsError,
    chart_view_watermark,
    fetch_public_charts,
    view_by_alias,
    weekly_global_top_artist_ids,
    weekly_global_top_song_track_ids,
)
from spotify_pipeline.clients.spotify import SpotifyApiError, get_artist, get_track
from spotify_pipeline.clients.spotify_auth import SpotifyAuthError, get_access_token
from spotify_pipeline.config import get_settings
from spotify_pipeline.db.postgres import (
    PostgresConfigError,
    call_with_db_retry,
    connect_postgres,
    require_db_url,
)
from spotify_pipeline.pipeline.bronze import write_raw_spotify
from spotify_pipeline.state.watermark import Watermark, WatermarkError

_SOURCE = "spotify_web_api"

_CHART_TYPE_TO_ALIAS = {
    "weekly_top_songs": ALIAS_SONGS,
    "weekly_top_artists": ALIAS_ARTISTS,
}


class EnrichSpotifyError(RuntimeError):
    """Raised when C9 enrich-spotify fails."""


def enrich_spotify(
    watermark: Watermark,
    *,
    client: httpx.Client | None = None,
    run_id: str | None = None,
    bronze_dir: Path | None = None,
    write_fs: bool = True,
) -> dict[str, Any]:
    """Fetch Spotify track/artist JSON for one watermark → C8 write_raw_spotify.

    ID source: live Charts public/v0 (same gate as ingest_charts).
    - weekly_top_songs: tracks + artists from track payloads
    - weekly_top_artists: artists only
    """
    alias = _CHART_TYPE_TO_ALIAS.get(watermark.chart_type)
    if alias is None:
        raise EnrichSpotifyError(
            f"unsupported chart_type for enrich-spotify: {watermark.chart_type!r}"
        )

    settings = get_settings()
    if not settings.spotify_client_id or not settings.spotify_client_secret:
        raise EnrichSpotifyError(
            "set SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET in .env"
        )
    try:
        require_db_url(settings)
    except PostgresConfigError as exc:
        raise EnrichSpotifyError(str(exc)) from exc

    db_url = settings.supabase_db_url.strip()
    rid = run_id or uuid.uuid4().hex
    fs_dir = settings.bronze_dir if write_fs else None
    if bronze_dir is not None:
        fs_dir = bronze_dir

    owns = client is None
    http = client or httpx.Client(timeout=60.0)
    track_count = 0
    artist_count = 0
    inserted = 0

    try:
        payload = fetch_public_charts(client=http)
        view = view_by_alias(payload, alias)
        live_date, live_type, live_country = chart_view_watermark(view)
        if not watermark.matches(live_date, live_type, live_country):
            raise EnrichSpotifyError(
                "live chart watermark mismatch: "
                f"requested={watermark.as_tuple()} "
                f"live={(live_date, live_type, live_country)}. "
                "Use the live chart_date from Charts public/v0."
            )

        track_ids: list[str] = []
        artist_ids: list[str] = []
        if watermark.chart_type == "weekly_top_songs":
            track_ids = weekly_global_top_song_track_ids(payload)
        else:
            artist_ids = weekly_global_top_artist_ids(payload)

        if not track_ids and not artist_ids:
            raise EnrichSpotifyError("no track/artist ids to enrich")

        token = get_access_token(
            settings.spotify_client_id,
            settings.spotify_client_secret,
            client=http,
        )
        access = str(token["access_token"])

        conn = connect_postgres(db_url)
        try:
            for track_id in track_ids:
                track_payload = get_track(access, track_id, client=http)

                def _write_track(
                    c: Any, _payload: dict = track_payload, _id: str = track_id
                ) -> None:
                    write_raw_spotify(
                        c,
                        run_id=rid,
                        source=_SOURCE,
                        entity="track",
                        spotify_id=_id,
                        payload=_payload,
                        bronze_dir=fs_dir,
                    )

                conn = call_with_db_retry(db_url, conn, _write_track)
                inserted += 1
                track_count += 1
                for aid in _artist_ids_from_track(track_payload):
                    if aid not in artist_ids:
                        artist_ids.append(aid)

            for artist_id in artist_ids:
                artist_payload = get_artist(access, artist_id, client=http)

                def _write_artist(
                    c: Any, _payload: dict = artist_payload, _id: str = artist_id
                ) -> None:
                    write_raw_spotify(
                        c,
                        run_id=rid,
                        source=_SOURCE,
                        entity="artist",
                        spotify_id=_id,
                        payload=_payload,
                        bronze_dir=fs_dir,
                    )

                conn = call_with_db_retry(db_url, conn, _write_artist)
                inserted += 1
                artist_count += 1
        finally:
            conn.close()
    except (
        ChartsError,
        SpotifyAuthError,
        SpotifyApiError,
        WatermarkError,
        httpx.HTTPError,
    ) as exc:
        raise EnrichSpotifyError(str(exc)) from exc
    finally:
        if owns:
            http.close()

    return {
        "run_id": rid,
        "watermark": watermark.as_tuple(),
        "track_count": track_count,
        "artist_count": artist_count,
        "inserted": inserted,
        "source": _SOURCE,
    }


def _artist_ids_from_track(track_payload: dict[str, Any]) -> list[str]:
    artists = track_payload.get("artists") or []
    if not isinstance(artists, list):
        return []
    ids: list[str] = []
    for item in artists:
        if not isinstance(item, dict):
            continue
        aid = str(item.get("id") or "").strip()
        if aid and aid not in ids:
            ids.append(aid)
    return ids
