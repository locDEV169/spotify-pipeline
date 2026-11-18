"""SPEC C5 — GET /v1/audio-features?ids= batch ≤40; map hits/misses; 429 retry.

Docs: https://reccobeats.com/docs/apis/get-audio-features
Rules: query ?ids= only (never path /:id); omit from content[] = miss, do not fail batch.
"""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import urlparse

import httpx

from spotify_pipeline.config import RECCOBEATS_API_BASE

_DEFAULT_BATCH_SIZE = 40
_DEFAULT_MAX_RETRIES = 3


class ReccoBeatsError(RuntimeError):
    """Raised when a ReccoBeats API call fails."""


def chunk_ids(ids: list[str], size: int = _DEFAULT_BATCH_SIZE) -> list[list[str]]:
    """Dedupe (preserve order) then chunk. SPEC Code Style."""
    if size < 1:
        raise ReccoBeatsError("chunk size must be >= 1")
    uniq = list(dict.fromkeys(i for i in ids if i))
    return [uniq[i : i + size] for i in range(0, len(uniq), size)]


def get_audio_features(
    ids: list[str],
    *,
    client: httpx.Client | None = None,
    timeout: float = 30.0,
    max_retries: int = _DEFAULT_MAX_RETRIES,
) -> dict[str, Any]:
    """GET /v1/audio-features?ids= for one batch (≤40 after dedupe)."""
    uniq = list(dict.fromkeys(i for i in ids if i))
    if not uniq:
        raise ReccoBeatsError("ids is required")
    if len(uniq) > _DEFAULT_BATCH_SIZE:
        raise ReccoBeatsError(
            f"batch size {len(uniq)} exceeds {_DEFAULT_BATCH_SIZE}; use chunk_ids first"
        )

    owns = client is None
    http = client or httpx.Client(timeout=timeout)
    url = f"{RECCOBEATS_API_BASE}/v1/audio-features"
    headers = {"Accept": "application/json"}
    params = {"ids": ",".join(uniq)}

    try:
        attempt = 0
        while True:
            response = http.get(url, params=params, headers=headers)
            if response.status_code == 429 and attempt < max_retries:
                sleep_s = _retry_after_seconds(response)
                time.sleep(sleep_s)
                attempt += 1
                continue
            if response.status_code != 200:
                raise ReccoBeatsError(_safe_api_error(response))
            payload = response.json()
            if not isinstance(payload, dict):
                raise ReccoBeatsError("audio-features: expected JSON object")
            return payload
    finally:
        if owns:
            http.close()


def audio_features_hits_misses(
    requested_ids: list[str],
    payload: dict[str, Any],
) -> tuple[list[str], list[str]]:
    """Map requested Spotify track ids to hits/misses via content[].href.

    ReccoBeats `id` is a UUID — do not treat it as a Spotify id (SPEC field notes).
    Misses are omitted from content[] without failing the batch (BR-5).
    """
    requested = list(dict.fromkeys(i for i in requested_ids if i))
    content = payload.get("content") or []
    hit_set: set[str] = set()
    if isinstance(content, list):
        for item in content:
            if not isinstance(item, dict):
                continue
            spotify_id = spotify_id_from_href(str(item.get("href") or ""))
            if spotify_id:
                hit_set.add(spotify_id)
    hits = [i for i in requested if i in hit_set]
    misses = [i for i in requested if i not in hit_set]
    return hits, misses


def spotify_id_from_href(href: str) -> str:
    """https://open.spotify.com/track/{id} → id."""
    href = (href or "").strip()
    if not href:
        return ""
    parsed = urlparse(href)
    if "open.spotify.com" not in (parsed.netloc or ""):
        return ""
    path = parsed.path.rstrip("/")
    if "/track/" not in path:
        return ""
    return path.rsplit("/", 1)[-1]


def _retry_after_seconds(response: httpx.Response) -> float:
    raw = response.headers.get("Retry-After", "1")
    try:
        return max(0.0, float(raw))
    except ValueError:
        return 1.0


def _safe_api_error(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return f"HTTP {response.status_code}: {response.text[:200] or '(empty body)'}"
    if isinstance(body, dict):
        status = body.get("status", response.status_code)
        message = body.get("message") or body.get("error") or body
        return f"HTTP {response.status_code}: status={status} message={message}"
    return f"HTTP {response.status_code}: {body}"
