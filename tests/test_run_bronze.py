"""Unit tests for C14 run_bronze (extract once → enrich fan-out)."""

from __future__ import annotations

from unittest.mock import patch

from spotify_pipeline.pipeline.bronze.extract_ids import ExtractedIds
from spotify_pipeline.pipeline.run import run_bronze
from spotify_pipeline.state.watermark import Watermark


def test_run_bronze_extracts_once_and_fans_out() -> None:
    wm = Watermark.parse("2026-11-12", "weekly_top_songs", "global")
    extracted = ExtractedIds(
        track_ids=["t1", "t2"],
        artist_ids=[],
        watermark=wm.as_tuple(),
        raw_charts_id=7,
    )

    with (
        patch(
            "spotify_pipeline.pipeline.run.ingest_charts",
            return_value={"run_id": "r", "entry_count": 2},
        ) as ingest,
        patch(
            "spotify_pipeline.pipeline.run.extract_ids",
            return_value=extracted,
        ) as extract,
        patch(
            "spotify_pipeline.pipeline.run.enrich_spotify",
            return_value={"inserted": 2, "track_count": 2, "artist_count": 0},
        ) as sp,
        patch(
            "spotify_pipeline.pipeline.run.enrich_reccobeats",
            return_value={"inserted": 1, "hits": 2, "misses": 0},
        ) as rb,
        patch("spotify_pipeline.pipeline.run.httpx.Client"),
    ):
        result = run_bronze(wm, run_id="shared", write_fs=False, ingest=True)

    ingest.assert_called_once()
    extract.assert_called_once_with(wm)
    sp.assert_called_once()
    rb.assert_called_once()
    assert sp.call_args.kwargs["track_ids"] == ["t1", "t2"]
    assert rb.call_args.kwargs["track_ids"] == ["t1", "t2"]
    assert sp.call_args.kwargs["run_id"] == "shared"
    assert rb.call_args.kwargs["run_id"] == "shared"
    assert result["extract"]["track_count"] == 2
    assert result["enrich_spotify"]["inserted"] == 2
    assert result["enrich_reccobeats"]["inserted"] == 1


def test_run_bronze_skip_ingest() -> None:
    wm = Watermark.parse("2026-11-12", "weekly_top_songs", "global")
    extracted = ExtractedIds(
        track_ids=["t1"],
        artist_ids=[],
        watermark=wm.as_tuple(),
    )

    with (
        patch("spotify_pipeline.pipeline.run.ingest_charts") as ingest,
        patch(
            "spotify_pipeline.pipeline.run.extract_ids",
            return_value=extracted,
        ),
        patch(
            "spotify_pipeline.pipeline.run.enrich_spotify",
            return_value={"inserted": 1},
        ),
        patch(
            "spotify_pipeline.pipeline.run.enrich_reccobeats",
            return_value={"inserted": 1},
        ),
        patch("spotify_pipeline.pipeline.run.httpx.Client"),
    ):
        result = run_bronze(wm, write_fs=False, ingest=False)

    ingest.assert_not_called()
    assert result["ingest"] is None
