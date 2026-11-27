"""Ops log music.pipeline_runs — SQL shape + best-effort (no live DB, no Airflow)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any
from unittest.mock import patch

from spotify_pipeline.pipeline import ops
from spotify_pipeline.state.watermark import Watermark


class _FakeConn:
    def __init__(self) -> None:
        self.sqls: list[str] = []
        self.closed = False

    def run(self, sql: str, **kwargs: Any) -> None:
        assert kwargs == {}, "Ops must use simple queries (no bind kwargs)"
        self.sqls.append(sql)

    def close(self) -> None:
        self.closed = True


@dataclass(frozen=True, slots=True)
class _Result:
    run_id: str
    chart_date: date
    watermark: tuple[str, str, str]


def _wm() -> Watermark:
    return Watermark.parse("2026-11-19", "weekly_top_songs", "global")


def _capture(fn, *args, **kwargs) -> tuple[str, _FakeConn]:
    conn = _FakeConn()
    with patch.object(ops, "connect_postgres", return_value=conn):
        fn(*args, **kwargs)
    return conn.sqls[0], conn


def test_record_start_upserts_running_with_watermark() -> None:
    sql, conn = _capture(ops.record_start, "spotify_weekly", "manual__1", "bronze", _wm())
    assert "INSERT INTO music.pipeline_runs" in sql
    assert "ON CONFLICT (dag_id, dag_run_id) DO UPDATE" in sql
    assert "'running'" in sql
    assert "CAST('2026-11-19' AS date)" in sql
    assert "finished_at" in sql and "NULL" in sql
    assert conn.closed


def test_record_success_merges_summary_and_final_closes_run() -> None:
    result = _Result("r1", date(2026, 11, 19), ("2026-11-19", "weekly_top_songs", "global"))
    sql, _ = _capture(
        ops.record_success, "spotify_weekly", "manual__1", "build_gold", result, final=True
    )
    assert "'success'" in sql
    assert "jsonb_build_object('build_gold'" in sql
    assert "music.pipeline_runs.summary || EXCLUDED.summary" in sql
    assert "2026-11-19" in sql  # date stringified, not a TypeError


def test_record_success_not_final_keeps_running() -> None:
    sql, _ = _capture(ops.record_success, "d", "r", "bronze", {"run_id": "x"})
    assert "'running'" in sql and "'success'" not in sql


def test_record_failure_sets_error_task_and_redacts_uri() -> None:
    msg = "OperationalError: could not connect postgresql://u:pw@host:6543/db"
    sql, _ = _capture(ops.record_failure, "d", "r", "build_silver", msg)
    assert "'failed'" in sql
    assert "pw@host" not in sql
    assert "<redacted-uri>" in sql
    assert "'build_silver'" in sql  # error_task


def test_clean_error_truncates() -> None:
    assert len(ops.clean_error("x" * 5000)) == 1000


def test_quotes_are_escaped() -> None:
    sql, _ = _capture(ops.record_failure, "d", "run'1", "bronze", "it's bad")
    assert "run''1" in sql and "it''s bad" in sql


def test_write_failure_never_raises() -> None:
    with patch.object(ops, "connect_postgres", side_effect=RuntimeError("db down")):
        ops.record_start("d", "r", "bronze", _wm())
        ops.record_failure("d", "r", "bronze", "boom")
