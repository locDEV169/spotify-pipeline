"""Unit tests for Charts public/v0 helpers (no live network)."""

from spotify_pipeline.clients.charts import (
    chart_view_watermark,
    spotify_id_from_uri,
    view_by_alias,
    weekly_global_top_artist_ids,
    weekly_global_top_song_track_ids,
)


def test_spotify_id_from_uri() -> None:
    assert spotify_id_from_uri("spotify:track:abc") == "abc"
    assert spotify_id_from_uri("spotify:artist:xyz") == "xyz"
    assert spotify_id_from_uri("") == ""


def test_parse_ids_and_watermark() -> None:
    assert spotify_id_from_uri("spotify:track:3h5T5JypYU7huFiVYhv1dr") == "3h5T5JypYU7huFiVYhv1dr"
    assert spotify_id_from_uri("spotify:artist:3TVXtAsR1Inumwj472S9r4") == "3TVXtAsR1Inumwj472S9r4"
    assert spotify_id_from_uri("") == ""


def test_parse_song_and_artist_ids_from_payload() -> None:
    payload = {
        "chartEntryViewResponses": [
            {
                "displayChart": {
                    "date": "2026-11-12",
                    "chartMetadata": {
                        "alias": "REGIONAL_GLOBAL_WEEKLY",
                        "dimensions": {"country": "GLOBAL"},
                    },
                },
                "entries": [
                    {"trackMetadata": {"trackUri": "spotify:track:aaa111"}},
                    {"trackMetadata": {"trackUri": "spotify:track:bbb222"}},
                ],
            },
            {
                "displayChart": {
                    "date": "2026-11-12",
                    "chartMetadata": {
                        "alias": "ARTIST_GLOBAL_WEEKLY",
                        "dimensions": {"country": "GLOBAL"},
                    },
                },
                "entries": [
                    {"artistMetadata": {"artistUri": "spotify:artist:ccc333"}},
                ],
            },
        ]
    }
    assert weekly_global_top_song_track_ids(payload, limit=10) == ["aaa111", "bbb222"]
    assert weekly_global_top_artist_ids(payload) == ["ccc333"]
    view = view_by_alias(payload, "REGIONAL_GLOBAL_WEEKLY")
    assert chart_view_watermark(view) == ("2026-11-12", "weekly_top_songs", "global")
