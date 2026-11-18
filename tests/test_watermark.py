"""Unit tests for C7 Watermark (no network)."""

import pytest

from spotify_pipeline.state.watermark import Watermark, WatermarkError


def test_parse_defaults() -> None:
    wm = Watermark.parse("2026-11-12")
    assert wm.chart_date == "2026-11-12"
    assert wm.chart_type == "weekly_top_songs"
    assert wm.country == "global"
    assert wm.as_tuple() == ("2026-11-12", "weekly_top_songs", "global")


def test_parse_normalizes_case() -> None:
    wm = Watermark.parse("2026-11-12", chart_type="Weekly_Top_Songs", country="GLOBAL")
    assert wm.chart_type == "weekly_top_songs"
    assert wm.country == "global"


def test_parse_rejects_bad_date() -> None:
    with pytest.raises(WatermarkError, match="YYYY-MM-DD"):
        Watermark.parse("11-12-2026")
    with pytest.raises(WatermarkError, match="required"):
        Watermark.parse("")


def test_parse_rejects_unknown_chart_type() -> None:
    with pytest.raises(WatermarkError, match="unknown chart_type"):
        Watermark.parse("2026-11-12", chart_type="daily_top_200")


def test_matches() -> None:
    wm = Watermark.parse("2026-11-12", "weekly_top_songs", "global")
    assert wm.matches("2026-11-12", "weekly_top_songs", "global")
    assert not wm.matches("2026-11-05", "weekly_top_songs", "global")
    assert not wm.matches(None, "weekly_top_songs", "global")
