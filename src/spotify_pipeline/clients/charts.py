"""SPEC C3 — Fetch Charts public/v0; parse trackUri / artistUri.

MVP: unauthenticated weekly Global Top Songs + Top Artists (≈50 each).
auth/v0 deferred (⚠️). Learning/demo only — Charts is unofficial.
"""

from __future__ import annotations

from typing import Any

import httpx

from spotify_pipeline.config import CHARTS_PUBLIC_URL

_ALIAS_SONGS = "REGIONAL_GLOBAL_WEEKLY"
_ALIAS_ARTISTS = "ARTIST_GLOBAL_WEEKLY"


class ChartsError(RuntimeError):
    """Raised when Charts public/v0 fetch or parse fails."""


def spotify_id_from_uri(uri: str) -> str:
    """spotify:track:xxx / spotify:artist:xxx → Base-62 id."""
    uri = (uri or "").strip()
    if not uri:
        return ""
    return uri.rsplit(":", 1)[-1]


def fetch_public_charts(
    *,
    client: httpx.Client | None = None,
    timeout: float = 60.0,
) -> dict[str, Any]:
    """GET public/v0/charts (no auth)."""
    owns = client is None
    http = client or httpx.Client(timeout=timeout)
    try:
        response = http.get(
            CHARTS_PUBLIC_URL,
            headers={
                "Accept": "application/json",
                "app-platform": "Browser",
            },
        )
    finally:
        if owns:
            http.close()

    if response.status_code != 200:
        raise ChartsError(f"charts public/v0 HTTP {response.status_code}")
    payload = response.json()
    if not isinstance(payload, dict):
        raise ChartsError("charts public/v0: expected JSON object")
    return payload


def _view_by_alias(payload: dict[str, Any], alias: str) -> dict[str, Any]:
    views = payload.get("chartEntryViewResponses") or []
    for view in views:
        if not isinstance(view, dict):
            continue
        display = view.get("displayChart") or {}
        meta = display.get("chartMetadata") or {}
        if meta.get("alias") == alias:
            return view
    raise ChartsError(f"charts public/v0: missing alias {alias}")


def weekly_global_top_song_track_ids(
    payload: dict[str, Any] | None = None,
    *,
    client: httpx.Client | None = None,
    limit: int | None = 50,
) -> list[str]:
    """Ordered unique Spotify track ids from Weekly Top Songs: Global."""
    data = payload if payload is not None else fetch_public_charts(client=client)
    view = _view_by_alias(data, _ALIAS_SONGS)
    ids: list[str] = []
    for entry in view.get("entries") or []:
        if not isinstance(entry, dict):
            continue
        meta = entry.get("trackMetadata") or {}
        track_id = spotify_id_from_uri(str(meta.get("trackUri") or ""))
        if track_id:
            ids.append(track_id)
    ids = list(dict.fromkeys(ids))
    if limit is not None:
        ids = ids[:limit]
    return ids


def weekly_global_top_artist_ids(
    payload: dict[str, Any] | None = None,
    *,
    client: httpx.Client | None = None,
    limit: int | None = 50,
) -> list[str]:
    """Ordered unique Spotify artist ids from Weekly Top Artists: Global."""
    data = payload if payload is not None else fetch_public_charts(client=client)
    view = _view_by_alias(data, _ALIAS_ARTISTS)
    ids: list[str] = []
    for entry in view.get("entries") or []:
        if not isinstance(entry, dict):
            continue
        meta = entry.get("artistMetadata") or {}
        artist_id = spotify_id_from_uri(str(meta.get("artistUri") or ""))
        if artist_id:
            ids.append(artist_id)
    ids = list(dict.fromkeys(ids))
    if limit is not None:
        ids = ids[:limit]
    return ids
