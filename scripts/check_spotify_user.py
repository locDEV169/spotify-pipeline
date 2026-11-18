#!/usr/bin/env python3
"""Smoke-check user-scoped Spotify API: refresh_token → access_token → GET /v1/me + /v1/me/playlists.

Usage (repo root, venv active, .env has SPOTIFY_REFRESH_TOKEN from scripts/spotify_login.py):
    python scripts/check_spotify_user.py

No browser needed. Never prints secrets or tokens.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

try:
    import httpx
except ModuleNotFoundError:
    print(
        'FAIL: thiếu httpx. Activate venv rồi: python -m pip install -e ".[dev]"',
        file=sys.stderr,
    )
    raise SystemExit(2) from None

from spotify_pipeline.clients.spotify_auth import SpotifyAuthError, refresh_access_token
from spotify_pipeline.config import SPOTIFY_API_BASE, get_settings

_HINTS = {
    401: "token sai/hết hạn hoặc là token Client Credentials (không dùng được cho /me).",
    403: "tài khoản chưa được thêm vào User Management của app, hoặc thiếu scope / chưa Premium.",
}


def _get(client: httpx.Client, token: str, path: str) -> dict:
    r = client.get(
        f"{SPOTIFY_API_BASE}{path}", headers={"Authorization": f"Bearer {token}"}
    )
    if r.status_code != 200:
        try:
            msg = r.json().get("error", {}).get("message", r.text[:200])
        except ValueError:
            msg = r.text[:200]
        hint = _HINTS.get(r.status_code, "")
        raise RuntimeError(f"GET {path} → HTTP {r.status_code}: {msg}. {hint}")
    return r.json()


def main() -> int:
    s = get_settings()
    try:
        with httpx.Client(timeout=30.0) as client:
            tok = refresh_access_token(
                s.spotify_client_id,
                s.spotify_client_secret,
                s.spotify_refresh_token,
                client=client,
            )
            access = str(tok["access_token"])
            print(f"OK refresh → access_token expires_in={tok.get('expires_in')}s")
            if tok.get("refresh_token"):
                print(
                    "NOTE: Spotify trả refresh_token mới — chạy lại spotify_login.py --save nếu refresh lỗi sau này."
                )

            me = _get(client, access, "/me")
            print(
                f"OK /me: {me.get('display_name')} ({me.get('id')}) product={me.get('product')}"
            )

            pl = _get(client, access, "/me/playlists?limit=50")
            items = pl.get("items") or []
            print(f"OK /me/playlists: {len(items)} / total={pl.get('total')}")
            for p in items:
                if isinstance(p, dict):
                    owner = (p.get("owner") or {}).get("id")
                    print(f"  - {p.get('id')} | {p.get('name')} | owner={owner}")
    except (SpotifyAuthError, RuntimeError, httpx.HTTPError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print("Spotify user smoke-check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
