"""Unit tests for ReccoBeats C5 helpers (no live network)."""

from unittest.mock import MagicMock

import httpx
import pytest

from spotify_pipeline.clients.reccobeats import (
    ReccoBeatsError,
    audio_features_hits_misses,
    chunk_ids,
    get_audio_features,
    spotify_id_from_href,
)


def test_chunk_ids_dedupes_preserves_order_and_splits() -> None:
    ids = [f"id{i}" for i in range(41)] + ["id0", "id1"]
    chunks = chunk_ids(ids, size=40)
    assert len(chunks) == 2
    assert len(chunks[0]) == 40
    assert len(chunks[1]) == 1
    assert chunks[0][0] == "id0"
    assert chunks[1][0] == "id40"


def test_chunk_ids_empty() -> None:
    assert chunk_ids([]) == []
    assert chunk_ids(["", ""]) == []


def test_spotify_id_from_href() -> None:
    assert (
        spotify_id_from_href("https://open.spotify.com/track/003vvx7Niy0yvhvHt4a68B")
        == "003vvx7Niy0yvhvHt4a68B"
    )
    assert spotify_id_from_href("") == ""
    assert spotify_id_from_href("https://api.reccobeats.com/v1/track/uuid") == ""


def test_audio_features_hits_misses_partial() -> None:
    requested = ["aaa", "bbb", "ccc"]
    payload = {
        "content": [
            {
                "id": "uuid-1",
                "href": "https://open.spotify.com/track/aaa",
            },
            {
                "id": "uuid-2",
                "href": "https://open.spotify.com/track/ccc",
            },
        ]
    }
    hits, misses = audio_features_hits_misses(requested, payload)
    assert hits == ["aaa", "ccc"]
    assert misses == ["bbb"]


def test_get_audio_features_rejects_over_40() -> None:
    with pytest.raises(ReccoBeatsError, match="exceeds 40"):
        get_audio_features([f"id{i}" for i in range(41)])


def test_get_audio_features_429_then_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps: list[float] = []
    monkeypatch.setattr(
        "spotify_pipeline.clients.reccobeats.time.sleep",
        lambda s: sleeps.append(s),
    )

    ok = httpx.Response(
        200,
        json={"content": []},
        request=httpx.Request("GET", "https://api.reccobeats.com/v1/audio-features"),
    )
    limited = httpx.Response(
        429,
        headers={"Retry-After": "0.01"},
        request=httpx.Request("GET", "https://api.reccobeats.com/v1/audio-features"),
    )

    client = MagicMock()
    client.get.side_effect = [limited, ok]

    payload = get_audio_features(["aaa"], client=client, max_retries=2)
    assert payload == {"content": []}
    assert sleeps == [0.01]
    assert client.get.call_count == 2
    params = client.get.call_args.kwargs["params"]
    assert params["ids"] == "aaa"
    # query ?ids= — never path /:id
    assert client.get.call_args.args[0].endswith("/v1/audio-features")
