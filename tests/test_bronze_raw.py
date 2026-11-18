"""Unit tests for C8 bronze raw_* writers (no live DB)."""

from __future__ import annotations

import json
from typing import Any

from spotify_pipeline.pipeline.bronze import (
    write_raw_charts,
    write_raw_reccobeats,
    write_raw_spotify,
)


class _FakeConn:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def run(self, sql: str, **kwargs: Any) -> None:
        self.calls.append((sql, kwargs))


def test_write_raw_charts() -> None:
    conn = _FakeConn()
    payload = {"entries": [{"rank": 1}]}
    write_raw_charts(
        conn,
        run_id="r1",
        source="charts_public_v0",
        chart_date="2026-11-12",
        chart_type="weekly_top_songs",
        country="global",
        payload=payload,
    )
    assert len(conn.calls) == 1
    sql, kwargs = conn.calls[0]
    assert "music.raw_charts" in sql
    assert "CAST(:chart_date AS date)" in sql
    assert kwargs["run_id"] == "r1"
    assert kwargs["chart_type"] == "weekly_top_songs"
    assert json.loads(kwargs["payload"]) == payload


def test_write_raw_spotify() -> None:
    conn = _FakeConn()
    payload = {"id": "abc", "name": "Song"}
    write_raw_spotify(
        conn,
        run_id="r2",
        source="spotify_web_api",
        entity="track",
        spotify_id="abc",
        payload=payload,
    )
    sql, kwargs = conn.calls[0]
    assert "music.raw_spotify" in sql
    assert kwargs["entity"] == "track"
    assert kwargs["spotify_id"] == "abc"
    assert json.loads(kwargs["payload"]) == payload


def test_write_raw_reccobeats() -> None:
    conn = _FakeConn()
    payload = {"content": []}
    ids = ["aaa", "bbb"]
    write_raw_reccobeats(
        conn,
        run_id="r3",
        source="reccobeats",
        endpoint="audio-features",
        spotify_track_ids=ids,
        payload=payload,
    )
    sql, kwargs = conn.calls[0]
    assert "music.raw_reccobeats" in sql
    assert kwargs["endpoint"] == "audio-features"
    assert kwargs["spotify_track_ids"] == ids
    assert json.loads(kwargs["payload"]) == payload
