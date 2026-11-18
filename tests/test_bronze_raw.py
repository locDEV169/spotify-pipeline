"""Unit tests for C8 bronze raw_* writers (no live DB)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from spotify_pipeline.pipeline.bronze import (
    write_raw_charts,
    write_raw_reccobeats,
    write_raw_spotify,
)


class _FakeConn:
    def __init__(self) -> None:
        self.sqls: list[str] = []

    def run(self, sql: str, **kwargs: Any) -> None:
        assert kwargs == {}, "C8 must use simple queries (no bind kwargs)"
        self.sqls.append(sql)


def test_write_raw_charts_simple_sql() -> None:
    conn = _FakeConn()
    write_raw_charts(
        conn,
        run_id="r1",
        source="charts_public_v0",
        chart_date="2026-11-12",
        chart_type="weekly_top_songs",
        country="global",
        payload={"entries": [{"rank": 1}]},
    )
    sql = conn.sqls[0]
    assert "INSERT INTO music.raw_charts" in sql
    assert "CAST('2026-11-12' AS date)" in sql
    assert "::jsonb" in sql
    assert "weekly_top_songs" in sql


def test_write_raw_spotify_escapes_quotes() -> None:
    conn = _FakeConn()
    write_raw_spotify(
        conn,
        run_id="r2",
        source="spotify_web_api",
        entity="track",
        spotify_id="abc",
        payload={"name": "It's live", "uri": "spotify:track:abc"},
    )
    sql = conn.sqls[0]
    assert "INSERT INTO music.raw_spotify" in sql
    assert "It's live" in sql or "It''s live" in sql
    assert "spotify:track:abc" in sql


def test_write_raw_reccobeats_text_array() -> None:
    conn = _FakeConn()
    write_raw_reccobeats(
        conn,
        run_id="r3",
        source="reccobeats",
        endpoint="audio-features",
        spotify_track_ids=["aaa", "bbb"],
        payload={"content": []},
    )
    sql = conn.sqls[0]
    assert "INSERT INTO music.raw_reccobeats" in sql
    assert "ARRAY['aaa', 'bbb']::text[]" in sql


def test_dual_write_filesystem_envelope(tmp_path: Path) -> None:
    conn = _FakeConn()
    write_raw_spotify(
        conn,
        run_id="rfs",
        source="spotify_web_api",
        entity="track",
        spotify_id="abc123",
        payload={"name": "Song"},
        bronze_dir=tmp_path,
    )
    files = list(tmp_path.rglob("abc123.json"))
    assert len(files) == 1
    data = json.loads(files[0].read_text(encoding="utf-8"))
    assert "ingested_at" in data
    assert data["run_id"] == "rfs"
    assert data["spotify_id"] == "abc123"
    assert data["payload"]["name"] == "Song"


def test_dual_write_charts_path(tmp_path: Path) -> None:
    conn = _FakeConn()
    write_raw_charts(
        conn,
        run_id="rc",
        source="charts_public_v0",
        chart_date="2026-11-12",
        chart_type="weekly_top_songs",
        country="global",
        payload={"entries": []},
        bronze_dir=tmp_path,
    )
    path = (
        tmp_path
        / "charts"
        / "public_v0"
        / "chart_date=2026-11-12"
        / "global_weekly_top_songs.json"
    )
    assert path.is_file()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["ingested_at"]
    assert data["chart_type"] == "weekly_top_songs"
