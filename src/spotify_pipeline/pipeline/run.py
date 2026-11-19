"""SPEC C14 — One cycle orchestration (Bronze Stage 4 fidelity first).

Logical fan-out (Q-B=2 MVP): extract IDs once from Bronze, then call
enrich-spotify and enrich-reccobeats with the same ID set (sequential in-process;
branches do not depend on each other). Silver/Gold/report deferred.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import httpx

from spotify_pipeline.pipeline.enrich.reccobeats import (
    EnrichReccoBeatsError,
    enrich_reccobeats,
)
from spotify_pipeline.pipeline.enrich.spotify import EnrichSpotifyError, enrich_spotify
from spotify_pipeline.pipeline.bronze.extract_ids import ExtractIdsError, extract_ids
from spotify_pipeline.pipeline.bronze.ingest_charts import IngestChartsError, ingest_charts
from spotify_pipeline.state.watermark import Watermark


class RunError(RuntimeError):
    """Raised when C14 run (Bronze path) fails."""


def run_bronze(
    watermark: Watermark,
    *,
    client: httpx.Client | None = None,
    run_id: str | None = None,
    bronze_dir: Path | None = None,
    write_fs: bool = True,
    ingest: bool = True,
) -> dict[str, Any]:
    """Bronze cycle: optional ingest → extract once → Spotify + ReccoBeats.

    For ``weekly_top_songs`` both enrich branches run.
    For ``weekly_top_artists`` only enrich-spotify runs (no ReccoBeats tracks).
    """
    rid = run_id or uuid.uuid4().hex
    owns = client is None
    http = client or httpx.Client(timeout=60.0)
    summary: dict[str, Any] = {
        "run_id": rid,
        "watermark": watermark.as_tuple(),
        "ingest": None,
        "extract": None,
        "enrich_spotify": None,
        "enrich_reccobeats": None,
    }

    try:
        if ingest:
            try:
                summary["ingest"] = ingest_charts(
                    watermark,
                    client=http,
                    run_id=rid,
                    bronze_dir=bronze_dir,
                    write_fs=write_fs,
                )
            except IngestChartsError as exc:
                raise RunError(str(exc)) from exc

        try:
            extracted = extract_ids(watermark)
        except ExtractIdsError as exc:
            raise RunError(str(exc)) from exc

        summary["extract"] = {
            "track_count": len(extracted.track_ids),
            "artist_count": len(extracted.artist_ids),
            "raw_charts_id": extracted.raw_charts_id,
        }

        try:
            summary["enrich_spotify"] = enrich_spotify(
                watermark,
                client=http,
                run_id=rid,
                bronze_dir=bronze_dir,
                write_fs=write_fs,
                track_ids=list(extracted.track_ids),
                artist_ids=list(extracted.artist_ids),
            )
        except EnrichSpotifyError as exc:
            raise RunError(str(exc)) from exc

        if watermark.chart_type == "weekly_top_songs":
            try:
                summary["enrich_reccobeats"] = enrich_reccobeats(
                    watermark,
                    client=http,
                    run_id=rid,
                    bronze_dir=bronze_dir,
                    write_fs=write_fs,
                    track_ids=list(extracted.track_ids),
                )
            except EnrichReccoBeatsError as exc:
                raise RunError(str(exc)) from exc
    finally:
        if owns:
            http.close()

    return summary
