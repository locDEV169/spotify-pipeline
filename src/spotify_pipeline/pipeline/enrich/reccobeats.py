"""SPEC C9 — ReccoBeats audio-features enrich → Bronze (watermark-scoped)."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import httpx

from spotify_pipeline.clients.reccobeats import (
    ReccoBeatsError,
    audio_features_hits_misses,
    chunk_ids,
    get_audio_features,
)
from spotify_pipeline.config import get_settings
from spotify_pipeline.db.postgres import (
    PostgresConfigError,
    call_with_db_retry,
    connect_postgres,
    require_db_url,
)
from spotify_pipeline.pipeline.bronze import write_raw_reccobeats
from spotify_pipeline.pipeline.bronze.extract_ids import ExtractIdsError, extract_ids
from spotify_pipeline.state.watermark import Watermark, WatermarkError

_SOURCE = "reccobeats"
_ENDPOINT = "audio-features"


class EnrichReccoBeatsError(RuntimeError):
    """Raised when C9 enrich-reccobeats fails."""


def enrich_reccobeats(
    watermark: Watermark,
    *,
    client: httpx.Client | None = None,
    run_id: str | None = None,
    bronze_dir: Path | None = None,
    write_fs: bool = True,
    track_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Fetch ReccoBeats audio-features for one watermark → C8 write_raw_reccobeats.

    Requires chart_type=weekly_top_songs. Batches ≤40. Misses do not fail the run.
    ID source (Q-A=2): Bronze via extract_ids, unless track_ids injected (run fan-out).
    """
    if watermark.chart_type != "weekly_top_songs":
        raise EnrichReccoBeatsError(
            "enrich-reccobeats requires chart_type=weekly_top_songs "
            f"(got {watermark.chart_type!r})"
        )

    settings = get_settings()
    try:
        require_db_url(settings)
    except PostgresConfigError as exc:
        raise EnrichReccoBeatsError(str(exc)) from exc

    db_url = settings.supabase_db_url.strip()
    rid = run_id or uuid.uuid4().hex
    fs_dir = settings.bronze_dir if write_fs else None
    if bronze_dir is not None:
        fs_dir = bronze_dir
    batch_size = settings.reccobeats_batch_size or 40

    try:
        if track_ids is None:
            extracted = extract_ids(watermark)
            track_ids = list(extracted.track_ids)
        else:
            track_ids = list(track_ids)
    except ExtractIdsError as exc:
        raise EnrichReccoBeatsError(str(exc)) from exc

    if not track_ids:
        raise EnrichReccoBeatsError("no track ids to enrich")

    owns = client is None
    http = client or httpx.Client(timeout=60.0)
    hits_total = 0
    misses_total = 0
    inserted = 0
    batches = chunk_ids(track_ids, size=batch_size)

    try:
        conn = connect_postgres(db_url)
        try:
            for batch in batches:
                features = get_audio_features(batch, client=http)
                hits, misses = audio_features_hits_misses(batch, features)
                hits_total += len(hits)
                misses_total += len(misses)

                def _write(
                    c: Any, _batch: list[str] = batch, _payload: dict = features
                ) -> None:
                    write_raw_reccobeats(
                        c,
                        run_id=rid,
                        source=_SOURCE,
                        endpoint=_ENDPOINT,
                        spotify_track_ids=_batch,
                        payload=_payload,
                        bronze_dir=fs_dir,
                    )

                conn = call_with_db_retry(db_url, conn, _write)
                inserted += 1
        finally:
            conn.close()
    except (ReccoBeatsError, WatermarkError, httpx.HTTPError) as exc:
        raise EnrichReccoBeatsError(str(exc)) from exc
    finally:
        if owns:
            http.close()

    return {
        "run_id": rid,
        "watermark": watermark.as_tuple(),
        "track_count": len(track_ids),
        "batch_count": len(batches),
        "hits": hits_total,
        "misses": misses_total,
        "inserted": inserted,
        "source": _SOURCE,
    }
