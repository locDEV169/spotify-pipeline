#!/usr/bin/env python3
"""One-time Spotify user login (Authorization Code flow) → refresh_token.

Usage (repo root, venv active, .env has SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET):
    python scripts/spotify_login.py            # prints refresh_token
    python scripts/spotify_login.py --save     # also writes SPOTIFY_REFRESH_TOKEN into .env
    python scripts/spotify_login.py --no-server  # no local server: paste the callback URL manually

What happens:
1. Starts a tiny HTTP server on the host/port of SPOTIFY_REDIRECT_URI (default 127.0.0.1:5000).
2. Opens the Spotify consent page in your browser → you log in and press Agree.
3. Your BROWSER is redirected to http://127.0.0.1:5000/callback?code=... → the server catches `code`.
4. Exchanges `code` for tokens. Keep the refresh_token; daily runs only need refresh (no browser).

Never prints the client secret or the full access token.
"""

from __future__ import annotations

import argparse
import re
import secrets
import sys
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

try:
    import httpx  # noqa: F401
except ModuleNotFoundError:
    print(
        "FAIL: dependency `httpx` not found. Activate the venv and run:\n"
        '  python -m pip install -e ".[dev]"',
        file=sys.stderr,
    )
    raise SystemExit(2) from None

from spotify_pipeline.clients.spotify_auth import (
    SpotifyAuthError,
    build_authorize_url,
    exchange_code,
)
from spotify_pipeline.config import get_settings


def _wait_for_callback(redirect_uri: str, expected_state: str) -> dict[str, str]:
    parsed = urllib.parse.urlparse(redirect_uri)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 80
    path = parsed.path or "/"
    result: dict[str, str] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            req = urllib.parse.urlparse(self.path)
            if req.path != path:
                self.send_response(404)
                self.end_headers()
                return
            q = urllib.parse.parse_qs(req.query)
            result.update({k: v[0] for k, v in q.items()})
            ok = "code" in result and result.get("state") == expected_state
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            msg = (
                "Đã nhận code. Quay lại terminal."
                if ok
                else f"Lỗi: {result.get('error', 'state không khớp')}. Xem terminal."
            )
            self.wfile.write(f"<h3>{msg}</h3>".encode())

        def log_message(self, *args: object) -> None:
            pass

    try:
        server = HTTPServer((host, port), Handler)
    except OSError as exc:
        raise SystemExit(
            f"FAIL: không mở được server {host}:{port} ({exc}). "
            "Cổng đang bị chiếm? Tắt app đang dùng cổng đó hoặc chạy với --no-server."
        ) from None
    print(f"Đang chờ callback tại {redirect_uri} ... (Ctrl+C để huỷ)")
    with server:
        while "code" not in result and "error" not in result:
            server.handle_request()
    return result


def _manual_callback() -> dict[str, str]:
    url = input(
        "Dán NGUYÊN URL trên thanh địa chỉ sau khi bấm Agree (…/callback?code=…): "
    ).strip()
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    return {k: v[0] for k, v in q.items()}


def _save_refresh_token(token: str) -> Path:
    env_path = _REPO_ROOT / ".env"
    text = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    line = f"SPOTIFY_REFRESH_TOKEN={token}"
    if re.search(r"(?m)^SPOTIFY_REFRESH_TOKEN=.*$", text):
        text = re.sub(r"(?m)^SPOTIFY_REFRESH_TOKEN=.*$", lambda _m: line, text)
    else:
        text = text.rstrip("\n") + ("\n" if text else "") + line + "\n"
    env_path.write_text(text, encoding="utf-8")
    return env_path


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--save", action="store_true", help="ghi SPOTIFY_REFRESH_TOKEN vào .env"
    )
    ap.add_argument(
        "--no-server",
        action="store_true",
        help="không mở server, dán URL callback bằng tay",
    )
    ap.add_argument(
        "--no-browser", action="store_true", help="chỉ in URL, không tự mở trình duyệt"
    )
    args = ap.parse_args()

    s = get_settings()
    if not s.spotify_client_id or not s.spotify_client_secret:
        print(
            "FAIL: thiếu SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET trong .env",
            file=sys.stderr,
        )
        return 2

    state = secrets.token_urlsafe(16)
    url = build_authorize_url(
        s.spotify_client_id, s.spotify_redirect_uri, state=state, show_dialog=True
    )
    print(
        "Redirect URI đang dùng (phải có y hệt trong Dashboard):",
        s.spotify_redirect_uri,
    )
    print("Mở URL này trên TRÌNH DUYỆT:\n", url, "\n")
    if not args.no_browser:
        webbrowser.open(url)

    result = (
        _manual_callback()
        if args.no_server
        else _wait_for_callback(s.spotify_redirect_uri, state)
    )

    if "error" in result:
        print(f"FAIL authorize: {result['error']}", file=sys.stderr)
        return 1
    if result.get("state") != state:
        print(
            "FAIL: state không khớp (URL cũ hoặc không phải của lần chạy này). Chạy lại.",
            file=sys.stderr,
        )
        return 1

    try:
        token = exchange_code(
            s.spotify_client_id,
            s.spotify_client_secret,
            result["code"],
            s.spotify_redirect_uri,
        )
    except SpotifyAuthError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    refresh = str(token.get("refresh_token") or "")
    print(
        f"OK access_token: {str(token['access_token'])[:8]}… expires_in={token.get('expires_in')}s"
    )
    print(f"OK scope: {token.get('scope')}")
    if not refresh:
        print("WARN: response không có refresh_token.", file=sys.stderr)
        return 1
    if args.save:
        path = _save_refresh_token(refresh)
        print(
            f"OK đã lưu SPOTIFY_REFRESH_TOKEN vào {path} (file này đã nằm trong .gitignore)"
        )
    else:
        print(
            "refresh_token (dán vào .env dòng SPOTIFY_REFRESH_TOKEN=..., KHÔNG commit):"
        )
        print(refresh)
    print("Xong. Test tiếp: python scripts/check_spotify_user.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
