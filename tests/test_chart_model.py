"""Unit tests for C6 ChartEntry extract/validate (no network)."""

import pytest

from spotify_pipeline.models.chart import (
    ChartEntry,
    ChartModelError,
    chart_entries_from_view,
)


def test_chart_entry_streams_optional() -> None:
    row = ChartEntry(track_id="abc", rank=1, prev_rank=2, streams=None)
    assert row.track_id == "abc"
    assert row.streams is None


def test_chart_entries_from_view_nested_chart_entry_data() -> None:
    view = {
        "entries": [
            {
                "chartEntryData": {"currentRank": 1, "previousRank": 2},
                "trackMetadata": {"trackUri": "spotify:track:aaa111"},
            },
            {
                "chartEntryData": {"currentRank": 2, "previousRank": 0},
                "trackMetadata": {"trackUri": "spotify:track:bbb222"},
            },
        ]
    }
    rows = chart_entries_from_view(view)
    assert [r.track_id for r in rows] == ["aaa111", "bbb222"]
    assert rows[0].rank == 1
    assert rows[1].prev_rank is None  # 0 treated as absent


def test_chart_entries_accepts_top_level_ranks() -> None:
    view = {
        "entries": [
            {
                "currentRank": 3,
                "trackMetadata": {"trackUri": "spotify:track:ccc333"},
            }
        ]
    }
    rows = chart_entries_from_view(view)
    assert rows[0].rank == 3


def test_chart_entries_empty_fails() -> None:
    with pytest.raises(ChartModelError, match="no entries"):
        chart_entries_from_view({"entries": []})
