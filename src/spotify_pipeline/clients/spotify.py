"""SPEC C4 — Tracks/artists; prefer batch ?ids= with /{id} fallback. Never call audio-features.

Track endpoint: https://developer.spotify.com/documentation/web-api/reference/get-track
"""

from __future__ import annotations

import httpx  # pyright: ignore[reportMissingImports]

from spotify_pipeline.config import SPOTIFY_API_BASE


class SpotifyApiError(RuntimeError):
    """Raised when a Spotify Web API call fails."""


def get_track(
    access_token: str,
    track_id: str,
    *,
    client: httpx.Client | None = None,
    timeout: float = 30.0,
) -> dict[str, object]:
    """GET /v1/tracks/{id} — single-track probe (Dev Mode–friendly)."""
    return _get_entity(access_token, "tracks", track_id, client=client, timeout=timeout)


def get_artist(
    access_token: str,
    artist_id: str,
    *,
    client: httpx.Client | None = None,
    timeout: float = 30.0,
) -> dict[str, object]:
    """GET /v1/artists/{id} — single-artist probe (Dev Mode–friendly)."""
    return _get_entity(access_token, "artists", artist_id, client=client, timeout=timeout)


def _get_entity(
    access_token: str,
    kind: str,
    entity_id: str,
    *,
    client: httpx.Client | None = None,
    timeout: float = 30.0,
) -> dict[str, object]:
    if not access_token:
        raise SpotifyApiError("access_token is required")
    if not entity_id:
        raise SpotifyApiError(f"{kind} id is required")

    owns_client = client is None
    http = client or httpx.Client(timeout=timeout)
    try:
        response = http.get(
            f"{SPOTIFY_API_BASE}/{kind}/{entity_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    finally:
        if owns_client:
            http.close()

    if response.status_code != 200:
        raise SpotifyApiError(_safe_api_error(response))
    return response.json()


def _safe_api_error(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return f"HTTP {response.status_code}: {response.text[:200] or '(empty body)'}"
    err = body.get("error")
    if isinstance(err, dict):
        status = err.get("status", response.status_code)
        message = err.get("message", "unknown")
        return f"HTTP {status}: {message}"
    return f"HTTP {response.status_code}: {body}"
