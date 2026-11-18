"""Unit tests for C8 bronze raw_* writers (no live DB)."""

from __future__ import annotations

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
