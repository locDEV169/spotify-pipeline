"""SPEC C9 — Enrich package (Spotify + ReccoBeats → Bronze)."""

from spotify_pipeline.pipeline.enrich.reccobeats import (
    EnrichReccoBeatsError,
    enrich_reccobeats,
)
from spotify_pipeline.pipeline.enrich.spotify import EnrichSpotifyError, enrich_spotify

__all__ = [
    "EnrichReccoBeatsError",
    "EnrichSpotifyError",
    "enrich_reccobeats",
    "enrich_spotify",
]
