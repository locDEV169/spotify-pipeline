"""Unit tests for Charts public/v0 helpers (no live network)."""

from spotify_pipeline.clients.charts import (
    spotify_id_from_uri,
    weekly_global_top_artist_ids,
    weekly_global_top_song_track_ids,
)


def test_spotify_id_from_uri() -> None:
    assert spotify_id_from_uri("spotify:track:3h5T5JypYU7huFiVYhv1dr") == "3h5T5JypYU7huFiVYhv1dr"
    assert spotify_id_from_uri("spotify:artist:3TVXtAsR1Inumwj472S9r4") == "3TVXtAsR1Inumwj472S9r4"
    assert spotify_id_from_uri("") == ""


def test_parse_song_and_artist_ids_from_payload() -> None:
    payload = {
        "chartEntryViewResponses": [
            {
                "displayChart": {
                    "chartMetadata": {"alias": "REGIONAL_GLOBAL_WEEKLY"},
                },
                "entries": [
                    {
                        "trackMetadata": {
                            "trackUri": "spotify:track:aaa111",
                            "artists": [
                                {"spotifyUri": "spotify:artist:should_not_use_here"},
                            ],
                        }
                    },
                    {"trackMetadata": {"trackUri": "spotify:track:bbb222"}},
                ],
            },
            {
                "displayChart": {
                    "chartMetadata": {"alias": "ARTIST_GLOBAL_WEEKLY"},
                },
                "entries": [
                    {"artistMetadata": {"artistUri": "spotify:artist:ccc333"}},
                    {"artistMetadata": {"artistUri": "spotify:artist:ddd444"}},
                ],
            },
        ]
    }
    assert weekly_global_top_song_track_ids(payload, limit=10) == ["aaa111", "bbb222"]
    assert weekly_global_top_artist_ids(payload, limit=10) == ["ccc333", "ddd444"]
    assert weekly_global_top_song_track_ids(payload, limit=1) == ["aaa111"]
