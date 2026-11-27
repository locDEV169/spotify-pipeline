"""Unit tests for music DDL migrate helper (no live DB)."""

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts" / "ddl"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import apply_music_ddl


def test_split_sql_skips_comments_and_splits_statements() -> None:
    sql = """
-- comment
CREATE SCHEMA IF NOT EXISTS music;
CREATE TABLE IF NOT EXISTS music.t (id int);
"""
    parts = apply_music_ddl._split_sql(sql)
    assert len(parts) == 2
    assert "CREATE SCHEMA IF NOT EXISTS music" in parts[0]
    assert "music.t" in parts[1]


def test_music_schema_is_idempotent_and_has_ops_objects() -> None:
    sql = apply_music_ddl._DEFAULT_SQL.read_text(encoding="utf-8")
    stmts = apply_music_ddl._split_sql(sql)
    assert not apply_music_ddl._FORBIDDEN.search(sql)
    idempotent = (
        "CREATE SCHEMA IF NOT EXISTS",
        "CREATE TABLE IF NOT EXISTS",
        "CREATE INDEX IF NOT EXISTS",
        "CREATE OR REPLACE VIEW",
    )
    for stmt in stmts:
        head = " ".join(stmt.split())
        assert head.startswith(idempotent), head
    joined = "\n".join(stmts)
    assert "music.ops_pipeline_health" in joined
    assert "music.pipeline_runs" in joined
