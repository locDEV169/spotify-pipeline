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
ORDER BY f.rank, f.track_id;
