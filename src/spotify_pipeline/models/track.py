"""SPEC C6 — Track / Artist models (Silver dims; deprecated fields Optional)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator


class TrackModelError(ValueError):
    """Raised when a Spotify track/artist payload cannot be mapped."""


class TrackMetadata(BaseModel):
    """Spotify Web API track → dim_track metadata columns (no ReccoBeats features)."""

    track_id: str = Field(min_length=1)
    track_name: str | None = None
    duration_ms: int | None = None
    explicit: bool | None = None
    album_id: str | None = None
    album_name: str | None = None
    release_date: str | None = None
    release_date_precision: str | None = None
    isrc: str | None = None
    track_popularity: int | None = None

    @field_validator("track_popularity")
    @classmethod
    def _popularity_range(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if value < 0 or value > 100:
            raise ValueError("track_popularity must be 0..100 when set")
        return value


class ArtistMetadata(BaseModel):
    """Spotify Web API artist → dim_artist columns."""

    artist_id: str = Field(min_length=1)
    artist_name: str | None = None
    genres: list[str] | None = None
    followers: int | None = None
    artist_popularity: int | None = None

    @field_validator("artist_popularity")
    @classmethod
    def _popularity_range(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if value < 0 or value > 100:
            raise ValueError("artist_popularity must be 0..100 when set")
        return value


@dataclass(frozen=True, slots=True)
class TrackArtistLink:
    """One bridge_track_artist row (artist_position 0-based)."""

    track_id: str
    artist_id: str
    artist_position: int
    artist_name: str | None = None


def track_from_spotify_payload(
    payload: dict[str, Any],
    *,
    spotify_id: str | None = None,
) -> TrackMetadata:
    """Map a Spotify GET /v1/tracks/{id} JSON object to TrackMetadata."""
    tid = str(payload.get("id") or spotify_id or "").strip()
    album = payload.get("album") if isinstance(payload.get("album"), dict) else {}
    external = (
        payload.get("external_ids")
        if isinstance(payload.get("external_ids"), dict)
        else {}
    )
    try:
        return TrackMetadata(
            track_id=tid,
            track_name=_str_or_none(payload.get("name")),
            duration_ms=_int_or_none(payload.get("duration_ms")),
            explicit=_bool_or_none(payload.get("explicit")),
            album_id=_str_or_none(album.get("id")),
            album_name=_str_or_none(album.get("name")),
            release_date=_str_or_none(album.get("release_date")),
            release_date_precision=_str_or_none(album.get("release_date_precision")),
            isrc=_str_or_none(external.get("isrc")),
            track_popularity=_int_or_none(payload.get("popularity")),
        )
    except ValidationError as exc:
        raise TrackModelError(
            f"invalid Spotify track payload: {exc.error_count()} validation error(s)"
        ) from exc


def artist_from_spotify_payload(
    payload: dict[str, Any],
    *,
    spotify_id: str | None = None,
) -> ArtistMetadata:
    """Map a Spotify GET /v1/artists/{id} JSON object to ArtistMetadata."""
    aid = str(payload.get("id") or spotify_id or "").strip()
    followers_obj = (
        payload.get("followers") if isinstance(payload.get("followers"), dict) else {}
    )
    genres_raw = payload.get("genres")
    genres: list[str] | None
    if genres_raw is None:
        genres = None
    elif isinstance(genres_raw, list):
        genres = [str(g) for g in genres_raw if g is not None and str(g).strip()]
    else:
        raise TrackModelError("artist.genres must be a list when set")
    try:
        return ArtistMetadata(
            artist_id=aid,
            artist_name=_str_or_none(payload.get("name")),
            genres=genres,
            followers=_int_or_none(followers_obj.get("total")),
            artist_popularity=_int_or_none(payload.get("popularity")),
        )
    except ValidationError as exc:
        raise TrackModelError(
            f"invalid Spotify artist payload: {exc.error_count()} validation error(s)"
        ) from exc


def bridge_links_from_track_payload(
    payload: dict[str, Any],
    *,
    track_id: str | None = None,
) -> list[TrackArtistLink]:
    """Build 0-based bridge links from track.artists[] (SQ-7)."""
    tid = str(payload.get("id") or track_id or "").strip()
    if not tid:
        raise TrackModelError("track id required for bridge links")
    artists = payload.get("artists") or []
    if not isinstance(artists, list):
        return []
    links: list[TrackArtistLink] = []
    seen: set[str] = set()
    for position, item in enumerate(artists):
        if not isinstance(item, dict):
            continue
        aid = str(item.get("id") or "").strip()
        if not aid or aid in seen:
            continue
        seen.add(aid)
        links.append(
            TrackArtistLink(
                track_id=tid,
                artist_id=aid,
                artist_position=position,
                artist_name=_str_or_none(item.get("name")),
            )
        )
    return links


def _str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _bool_or_none(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    raise TrackModelError(f"explicit must be bool when set, got {type(value).__name__}")
