"""SPEC C6 — ChartEntry model (streams Optional). Fail-fast after extract."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator

from spotify_pipeline.clients.charts import spotify_id_from_uri


class ChartEntry(BaseModel):
    """One chart ranking row (Silver grain preview; used to validate extract)."""

    track_id: str = Field(min_length=1)
    rank: int = Field(ge=1)
    prev_rank: int | None = None
    streams: int | None = None
    entry_status: str | None = None

    @field_validator("prev_rank")
    @classmethod
    def _prev_rank_positive(cls, value: int | None) -> int | None:
        if value is not None and value < 1:
            raise ValueError("prev_rank must be >= 1 when set")
        return value


class ChartModelError(ValueError):
    """Raised when chart entries cannot be validated."""


def chart_entries_from_view(view: dict[str, Any]) -> list[ChartEntry]:
    """Extract + validate ChartEntry list from a chartEntryViewResponse."""
    raw_entries = view.get("entries") or []
    if not isinstance(raw_entries, list) or not raw_entries:
        raise ChartModelError("chart view has no entries")

    out: list[ChartEntry] = []
    errors: list[str] = []
    for i, entry in enumerate(raw_entries):
        if not isinstance(entry, dict):
            errors.append(f"entry[{i}]: not an object")
            continue
        meta = entry.get("trackMetadata") or {}
        data = entry.get("chartEntryData") or {}
        if not isinstance(data, dict):
            data = {}
        # Live public/v0 nests ranks under chartEntryData; accept top-level too.
        track_id = spotify_id_from_uri(str(meta.get("trackUri") or ""))
        rank = data.get("currentRank", entry.get("currentRank"))
        prev = data.get("previousRank", entry.get("previousRank"))
        status_raw = data.get("entryStatus", entry.get("entryStatus"))
        entry_status = None
        if status_raw not in (None, ""):
            entry_status = str(status_raw).strip() or None
        try:
            out.append(
                ChartEntry(
                    track_id=track_id,
                    rank=rank,
                    prev_rank=prev if prev not in (0, None, "") else None,
                    streams=None,  # public/v0: always NULL
                    entry_status=entry_status,
                )
            )
        except ValidationError as exc:
            errors.append(f"entry[{i}]: {exc.error_count()} validation error(s)")

    if errors and not out:
        raise ChartModelError("; ".join(errors[:5]))
    if not out:
        raise ChartModelError("no valid ChartEntry rows extracted")
    return out
