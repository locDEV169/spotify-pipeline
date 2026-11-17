"""Offline tests for Spotify auth helpers (no network: httpx.MockTransport)."""

from __future__ import annotations

import urllib.parse

import httpx
import pytest

from spotify_pipeline.clients.spotify_auth import (
    SpotifyAuthError,
    build_authorize_url,
    exchange_code,
    refresh_access_token,
)

REDIRECT = "http://127.0.0.1:5000/callback"


def _client(captured: dict, status: int = 200, body: dict | None = None) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["form"] = dict(urllib.parse.parse_qsl(request.content.decode()))
        captured["auth"] = request.headers.get("Authorization", "")
        return httpx.Response(status, json=body or {"access_token": "AT", "refresh_token": "RT"})

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_authorize_url_has_exact_redirect_and_scope() -> None:
    url = build_authorize_url("cid", REDIRECT, state="s1")
    q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))
    assert url.startswith("https://accounts.spotify.com/authorize?")
    assert q["redirect_uri"] == REDIRECT  # no double slash, no localhost
    assert q["response_type"] == "code"
    assert "playlist-read-private" in q["scope"]
    assert q["state"] == "s1"


def test_exchange_code_sends_authorization_code_grant() -> None:
    cap: dict = {}
    tok = exchange_code("cid", "sec", "CODE", REDIRECT, client=_client(cap))
    assert tok["refresh_token"] == "RT"
    assert cap["url"] == "https://accounts.spotify.com/api/token"
    assert cap["form"] == {"grant_type": "authorization_code", "code": "CODE", "redirect_uri": REDIRECT}
    assert cap["auth"].startswith("Basic ")


def test_refresh_sends_refresh_grant() -> None:
    cap: dict = {}
    refresh_access_token("cid", "sec", "RT", client=_client(cap))
    assert cap["form"] == {"grant_type": "refresh_token", "refresh_token": "RT"}


def test_refresh_without_token_explains_next_step() -> None:
    with pytest.raises(SpotifyAuthError, match="spotify_login.py"):
        refresh_access_token("cid", "sec", "")


def test_oauth_error_is_surfaced() -> None:
    cap: dict = {}
    bad = _client(cap, 400, {"error": "invalid_grant", "error_description": "Invalid redirect URI"})
    with pytest.raises(SpotifyAuthError, match="invalid_grant: Invalid redirect URI"):
        exchange_code("cid", "sec", "CODE", REDIRECT, client=bad)
