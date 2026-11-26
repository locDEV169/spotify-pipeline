"""Read weekly chart data from Silver and assemble the dashboard response."""

from pathlib import Path

from spotify_pipeline.db.postgres import connect_postgres

_SQL_DIR = Path(__file__).resolve().parents[4] / "docs" / "sql" / "silver"


class ChartNotFound(Exception):
    """The requested week is not available in Silver."""


def read_chart(week: str | None) -> dict:
    weeks_sql = (_SQL_DIR / "dashboard_available_weeks.sql").read_text(encoding="utf-8")
    chart_sql = (_SQL_DIR / "dashboard_weekly_global.sql").read_text(encoding="utf-8")
    conn = connect_postgres()
    try:
        conn.run("START TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        dates = conn.run(weeks_sql)
        weeks = [str(row[0]) for row in dates]
        selected = week or (weeks[0] if weeks else None)
        if selected is not None and selected not in weeks:
            raise ChartNotFound("No chart available for this week")
        rows = [] if selected is None else conn.run(chart_sql, week=selected)
        tracks = []
        artists = {}
        for track_id, name, rank, previous, found, energy, dance, valence, tempo, members in rows:
            tracks.append({
                "id": track_id, "name": name or "Unknown track",
                "artist": ", ".join(member["name"] or "Unknown artist" for member in members)
                          or "Unknown artist",
                "rank": rank, "previousRank": previous, "featuresFound": bool(found),
                "energy": energy if found else None,
                "danceability": dance if found else None,
                "valence": valence if found else None,
                "tempo": tempo if found else None,
            })
            for member in members:
                artist = artists.setdefault(member["id"], {
                    "artist": member["name"] or "Unknown artist", "tracks": 0, "bestRank": rank,
                })
                artist["tracks"] += 1
                artist["bestRank"] = min(artist["bestRank"], rank)
        return {
            "week": selected, "weeks": weeks, "tracks": tracks,
            "artists": sorted(artists.values(), key=lambda row: (row["bestRank"], -row["tracks"], row["artist"])),
        }
    finally:
        conn.close()
