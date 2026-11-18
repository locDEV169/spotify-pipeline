"""SPEC C6 — AudioFeatures + features_found (ReccoBeats → dim_track)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ValidationError

from spotify_pipeline.clients.reccobeats import spotify_id_from_href


class AudioFeaturesModelError(ValueError):
    """Raised when a ReccoBeats audio-features item cannot be mapped."""


class AudioFeatures(BaseModel):
    """One ReccoBeats content[] hit mapped to dim_track feature columns."""

    track_id: str = Field(min_length=1)
    reccobeats_uuid: str | None = None
    href: str | None = None
    acousticness: float | None = None
    danceability: float | None = None
    energy: float | None = None
    instrumentalness: float | None = None
    liveness: float | None = None
    speechiness: float | None = None
    valence: float | None = None
    loudness: float | None = None
    tempo: float | None = None
    key: int | None = None
    mode: int | None = None
    features_found: bool = True


def audio_features_from_reccobeats_item(item: dict[str, Any]) -> AudioFeatures:
    """Map one ReccoBeats content[] object; Spotify id comes from href (not UUID)."""
    href = _str_or_none(item.get("href"))
    track_id = spotify_id_from_href(href or "")
    if not track_id:
        raise AudioFeaturesModelError("ReccoBeats item missing Spotify track href")
    try:
        return AudioFeatures(
            track_id=track_id,
            reccobeats_uuid=_str_or_none(item.get("id")),
            href=href,
            acousticness=_float_or_none(item.get("acousticness")),
            danceability=_float_or_none(item.get("danceability")),
            energy=_float_or_none(item.get("energy")),
            instrumentalness=_float_or_none(item.get("instrumentalness")),
            liveness=_float_or_none(item.get("liveness")),
            speechiness=_float_or_none(item.get("speechiness")),
            valence=_float_or_none(item.get("valence")),
            loudness=_float_or_none(item.get("loudness")),
            tempo=_float_or_none(item.get("tempo")),
            key=_int_or_none(item.get("key")),
            mode=_int_or_none(item.get("mode")),
            features_found=True,
        )
    except ValidationError as exc:
        raise AudioFeaturesModelError(
            f"invalid ReccoBeats features: {exc.error_count()} validation error(s)"
        ) from exc


def _str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)
