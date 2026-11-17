"""SPEC C4 — Spotify auth.

Two flows:
- Client Credentials (~1h token): catalog endpoints (/tracks/{id}, /artists/{id}, /albums/{id}).
  https://developer.spotify.com/documentation/web-api/tutorials/client-credentials-flow
- Authorization Code (user login, one-time consent): /v1/me/* endpoints (playlists, top items).
  https://developer.spotify.com/documentation/web-api/tutorials/code-flow
  After the first consent, keep the refresh_token and call refresh_access_token() — no browser needed.

Never log access tokens, refresh tokens or the client secret at call sites.
"""

from __future__ import annotations

import urllib.parse

import httpx  # pyright: ignore[reportMissingImports]

from spotify_pipeline.config import SPOTIFY_AUTHORIZE_URL, SPOTIFY_TOKEN_URL

DEFAULT_USER_SCOPES = "playlist-read-private playlist-read-collaborative user-top-read"


class SpotifyAuthError(RuntimeError):
    """Raised when a Spotify token request fails."""


def get_access_token(
    client_id: str,
    client_secret: str,
    *,
    client: httpx.Client | None = None,
    timeout: float = 30.0,
) -> dict[str, object]:
    """POST /api/token with grant_type=client_credentials.

    Returns the JSON body (`access_token`, `token_type`, `expires_in`).
    NOTE: this token has no user context, so /v1/me/* returns 401.
    """
    _require_client(client_id, client_secret)
    return _token_request(
        client_id,
        client_secret,
        {"grant_type": "client_credentials"},
        client=client,
        timeout=timeout,
    )


def build_authorize_url(
    client_id: str,
    redirect_uri: str,
    *,
    scope: str = DEFAULT_USER_SCOPES,
    state: str | None = None,
    show_dialog: bool = False,
) -> str:
    """URL to open in a BROWSER (not curl/Postman) for the user to log in and Agree."""
    if not client_id or not redirect_uri:
        raise SpotifyAuthError("client_id and redirect_uri are required")
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": scope,
    }
    if state:
        params["state"] = state
    if show_dialog:
        params["show_dialog"] = "true"
    return f"{SPOTIFY_AUTHORIZE_URL}?{urllib.parse.urlencode(params, quote_via=urllib.parse.quote)}"


def exchange_code(
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
    *,
    client: httpx.Client | None = None,
    timeout: float = 30.0,
) -> dict[str, object]:
    """Exchange the one-time `code` (from the callback URL) for access + refresh tokens.

    redirect_uri must be byte-identical to the one used in the authorize URL
    AND registered in the Spotify Dashboard.
    """
    _require_client(client_id, client_secret)
    if not code:
        raise SpotifyAuthError("code is required")
    return _token_request(
        client_id,
        client_secret,
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        },
        client=client,
        timeout=timeout,
    )


def refresh_access_token(
    client_id: str,
    client_secret: str,
    refresh_token: str,
    *,
    client: httpx.Client | None = None,
    timeout: float = 30.0,
) -> dict[str, object]:
    """Get a fresh user access token from a stored refresh_token (no browser).

    Spotify may return a new refresh_token; if present, store it and use it next time.
    """
    _require_client(client_id, client_secret)
    if not refresh_token:
        raise SpotifyAuthError(
            "SPOTIFY_REFRESH_TOKEN is empty — run `python scripts/spotify_login.py` once first"
        )
    return _token_request(
        client_id,
        client_secret,
        {"grant_type": "refresh_token", "refresh_token": refresh_token},
        client=client,
        timeout=timeout,
    )


def _require_client(client_id: str, client_secret: str) -> None:
    if not client_id or not client_secret:
        raise SpotifyAuthError(
            "SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET are required"
        )


def _token_request(
    client_id: str,
    client_secret: str,
    data: dict[str, str],
    *,
    client: httpx.Client | None,
    timeout: float,
) -> dict[str, object]:
    owns_client = client is None
    http = client or httpx.Client(timeout=timeout)
    try:
        response = http.post(
            SPOTIFY_TOKEN_URL,
            data=data,
            auth=(client_id, client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    finally:
        if owns_client:
            http.close()

    if response.status_code != 200:
        # OAuth error body may include error / error_description — never echo secrets.
        detail = _safe_oauth_error(response)
        raise SpotifyAuthError(
            f"token request failed HTTP {response.status_code}: {detail}"
        )

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
