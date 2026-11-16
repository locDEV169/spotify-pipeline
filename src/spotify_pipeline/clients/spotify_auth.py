"""SPEC C4 — Spotify Client Credentials token (~1h).

Auth flow: https://developer.spotify.com/documentation/web-api/tutorials/client-credentials-flow
"""

from __future__ import annotations

import httpx  # pyright: ignore[reportMissingImports]

from spotify_pipeline.config import SPOTIFY_TOKEN_URL


class SpotifyAuthError(RuntimeError):
    """Raised when Client Credentials token request fails."""


def get_access_token(
    client_id: str,
    client_secret: str,
    *,
    client: httpx.Client | None = None,
    timeout: float = 30.0,
) -> dict[str, object]:
    """POST /api/token with grant_type=client_credentials.

    Returns the JSON body (`access_token`, `token_type`, `expires_in`).
    Never log the access token at call sites.
    """
    if not client_id or not client_secret:
        raise SpotifyAuthError("SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET are required")

    owns_client = client is None
    http = client or httpx.Client(timeout=timeout)
    try:
        response = http.post(
            SPOTIFY_TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(client_id, client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    finally:
        if owns_client:
            http.close()

    if response.status_code != 200:
        # OAuth error body may include error / error_description — never echo secrets.
        detail = _safe_oauth_error(response)
        raise SpotifyAuthError(f"token request failed HTTP {response.status_code}: {detail}")

    payload = response.json()
    if "access_token" not in payload:
        raise SpotifyAuthError("token response missing access_token")
    return payload


def _safe_oauth_error(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text[:200] or "(empty body)"
    error = body.get("error", "unknown_error")
    description = body.get("error_description")
    if description:
        return f"{error}: {description}"
    return str(error)
