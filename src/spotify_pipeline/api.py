"""Read-only HTTP API for the weekly Global dashboard."""

from datetime import date

from flask import Flask, jsonify, request

from spotify_pipeline.db.postgres import connect_postgres


class ChartNotFound(Exception):
    pass


def read_chart(week: str | None) -> dict:
    conn = connect_postgres()
    try:
        conn.run("START TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        dates = conn.run("""
            SELECT DISTINCT chart_date FROM music.fact_chart
            WHERE chart_type = 'weekly_top_songs' AND country = 'global'
            ORDER BY chart_date DESC
        """)
        weeks = [str(row[0]) for row in dates]
        selected = week or (weeks[0] if weeks else None)
        if selected is not None and selected not in weeks:
            raise ChartNotFound("No chart available for this week")
        rows = [] if selected is None else conn.run("""
            SELECT f.track_id, t.track_name, f.rank, f.prev_rank,
                   t.features_found, t.energy, t.danceability, t.valence, t.tempo,
                   COALESCE(artists.members, '[]'::jsonb)
            FROM music.fact_chart f
            LEFT JOIN music.dim_track t ON t.track_id = f.track_id
            LEFT JOIN LATERAL (
                SELECT jsonb_agg(jsonb_build_object('id', a.artist_id, 'name', a.artist_name)
                                ORDER BY b.artist_position, a.artist_id) AS members
                FROM music.bridge_track_artist b
                JOIN music.dim_artist a ON a.artist_id = b.artist_id
                WHERE b.track_id = f.track_id
            ) artists ON true
            WHERE f.chart_date = :week AND f.chart_type = 'weekly_top_songs'
                  AND f.country = 'global'
            ORDER BY f.rank, f.track_id
        """, week=selected)
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


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/api/health")
    def health():
        return jsonify(status="ok", service="spotify-pipeline")

    @app.get("/api/charts")
    def charts():
        week = request.args.get("week")
        if week is not None:
            try:
                if date.fromisoformat(week).isoformat() != week:
                    raise ValueError
            except ValueError:
                return jsonify(error="week must be a valid YYYY-MM-DD date"), 400
        try:
            return jsonify(read_chart(week))
        except ChartNotFound:
            return jsonify(error="No chart available for this week"), 404
        except Exception as exc:
            # Database exception messages can contain connection details.
            app.logger.error("Chart read failed (%s)", type(exc).__name__)
            return jsonify(error="Chart data is unavailable. Check the backend database connection."), 503

    return app
