"""Unit tests for C6 TrackMetadata mapping (no network)."""

from __future__ import annotations

import pytest

from spotify_pipeline.models.track import (
    TrackModelError,
    track_from_spotify_payload,
)


def _spotify_track_payload(**overrides: object) -> dict:
    base = {
        "id": "aaa111",
        "name": "Song A",
        "duration_ms": 210000,
        "explicit": False,
        "popularity": 77,
        "external_ids": {"isrc": "USUM70000001"},
        "album": {
            "id": "alb1",
            "name": "Album A",
            "release_date": "2020-01-01",
            "release_date_precision": "day",
        },
    }
    base.update(overrides)
    return base


def test_track_from_spotify_payload_maps_metadata() -> None:
    row = track_from_spotify_payload(_spotify_track_payload())
    assert row.track_id == "aaa111"
    assert row.track_name == "Song A"
    assert row.duration_ms == 210000
    assert row.explicit is False
    assert row.album_id == "alb1"
    assert row.album_name == "Album A"
    assert row.release_date == "2020-01-01"
    assert row.release_date_precision == "day"
    assert row.isrc == "USUM70000001"
    assert row.track_popularity == 77


def test_track_popularity_nullable() -> None:
    row = track_from_spotify_payload(_spotify_track_payload(popularity=None))
    assert row.track_popularity is None


def test_track_uses_spotify_id_fallback() -> None:
    payload = _spotify_track_payload()
    del payload["id"]
    row = track_from_spotify_payload(payload, spotify_id="fallback99")
    assert row.track_id == "fallback99"


def test_track_missing_id_fails() -> None:
    payload = _spotify_track_payload()
    del payload["id"]
    with pytest.raises(TrackModelError):
        track_from_spotify_payload(payload)
