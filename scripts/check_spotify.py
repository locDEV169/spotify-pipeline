#!/usr/bin/env python3
"""Local smoke-check: Spotify Client Credentials + one Web API track read.

Usage (from repo root, with `.env` filled):
    python scripts/check_spotify.py

Success: exit 0 after token + GET /v1/tracks/{id}.
Never prints client secret or access token.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running without editable install (repo-root python scripts/...)
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

try:
    import httpx
except ModuleNotFoundError:
    venv_python = _REPO_ROOT / ".venv" / "Scripts" / "python.exe"
    print(
        "FAIL: dependency `httpx` not found in this Python.\n"
        "Activate the project venv first, then retry:\n"
        "  source .venv/Scripts/activate   # Git Bash\n"
        "  python -m pip install -e \".[dev]\"\n"
        f"Or run:  {venv_python} scripts/check_spotify.py",
        file=sys.stderr,
    )
    raise SystemExit(2) from None

from spotify_pipeline.clients.spotify import SpotifyApiError, get_track
from spotify_pipeline.clients.spotify_auth import SpotifyAuthError, get_access_token
from spotify_pipeline.config import get_settings

# SPEC E2E evidence example — The Killers – Mr. Brightside
PROBE_TRACK_ID = "003vvx7Niy0yvhvHt4a68B"


def main() -> int:
    settings = get_settings()
    if not settings.spotify_client_id or not settings.spotify_client_secret:
        print(
            "FAIL: set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in .env "
            "(see .env.example).",
            file=sys.stderr,
        )
        return 2

    try:
        with httpx.Client(timeout=30.0) as client:
            token = get_access_token(
                settings.spotify_client_id,
                settings.spotify_client_secret,
                client=client,
            )
            expires_in = token.get("expires_in")
            token_type = token.get("token_type")
            access_token = str(token["access_token"])

            print(f"OK token: type={token_type!s} expires_in={expires_in!s}s")

            track = get_track(access_token, PROBE_TRACK_ID, client=client)
            name = track.get("name", "?")
            track_id = track.get("id", PROBE_TRACK_ID)
            artists = track.get("artists") or []
            artist_names = ", ".join(
                str(a.get("name", "?")) for a in artists if isinstance(a, dict)
            ) or "?"
            print(f"OK track: {artist_names} – {name} ({track_id})")
    except (SpotifyAuthError, SpotifyApiError, httpx.HTTPError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    print("Spotify smoke-check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
