"""Unit tests for music DDL migrate helper (no live DB)."""

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
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
