"""G2 — gold_movers rank_delta + streams null-safe (no network)."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

from spotify_pipeline.pipeline.gold import (
    MoverRow,
    query_movers,
    sql_movers,
)
from spotify_pipeline.state.watermark import Watermark


def _wm() -> Watermark:
    return Watermark.parse("2026-11-12", "weekly_top_songs", "global")


def _settings() -> MagicMock:
    s = MagicMock()
    s.supabase_db_url = "postgresql://u:p@localhost/db"
    return s


def test_gold_queries_sql_has_movers_section() -> None:
    from spotify_pipeline.pipeline.gold import _SQL_GOLD_QUERIES

    assert _SQL_GOLD_QUERIES.is_file()
    raw = _SQL_GOLD_QUERIES.read_text(encoding="utf-8")
    assert "-- @@query: movers" in raw
    assert "FROM music.gold_movers" in raw
    assert "/*__WHERE__*/" in raw
    assert "prev_rank IS NULL" in raw  # GQ-2 documented in comment


def test_sql_movers_injects_watermark() -> None:
    sql = sql_movers(_wm())
    assert "FROM music.gold_movers" in sql
    assert "/*__WHERE__*/" not in sql
    assert "2026-11-12" in sql
    assert "weekly_top_songs" in sql
    assert "global" in sql


def test_query_movers_maps_delta_sign_and_null_streams() -> None:
    db = MagicMock()
    db.run.return_value = [
        # climbed: prev 5 → rank 2 → delta +3; streams NULL (public/v0)
        (date(2026, 11, 12), "weekly_top_songs", "global", "up1", "Up Song", 2, 5, 3, None),
        # fell: prev 2 → rank 5 → delta -3; streams present
        (date(2026, 11, 12), "weekly_top_songs", "global", "dn1", None, 5, 2, -3, 1000),
    ]

    with (
        patch("spotify_pipeline.pipeline.gold.readers.get_settings", return_value=_settings()),
        patch("spotify_pipeline.pipeline.gold.readers.require_db_url"),
        patch("spotify_pipeline.pipeline.gold.readers.connect_postgres", return_value=db),
    ):
        rows = query_movers(_wm())

    assert rows == [
        MoverRow(
            track_id="up1",
            track_name="Up Song",
            rank=2,
            prev_rank=5,
            rank_delta=3,
            streams=None,
        ),
        MoverRow(
            track_id="dn1",
            track_name=None,
            rank=5,
            prev_rank=2,
            rank_delta=-3,
            streams=1000,
        ),
    ]
    # SPEC: rank_delta = prev_rank - rank
    assert rows[0].rank_delta == rows[0].prev_rank - rows[0].rank
    assert rows[1].rank_delta == rows[1].prev_rank - rows[1].rank
    sql = db.run.call_args[0][0]
    assert "FROM music.gold_movers" in sql
    db.close.assert_called_once()


def test_query_movers_empty_returns_list() -> None:
    db = MagicMock()
    db.run.return_value = []

    with (
        patch("spotify_pipeline.pipeline.gold.readers.get_settings", return_value=_settings()),
        patch("spotify_pipeline.pipeline.gold.readers.require_db_url"),
        patch("spotify_pipeline.pipeline.gold.readers.connect_postgres", return_value=db),
    ):
        assert query_movers(_wm()) == []
