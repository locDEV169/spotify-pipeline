-- Silver W5 / SPEC BR-6: chart rows survive missing dim_track / features.
-- Python helper: spotify_pipeline.pipeline.silver.sql_fact_chart_left_join_dim_track
-- Placeholder /*__WHERE__*/ is replaced with an optional watermark filter (or empty).

SELECT
    f.chart_date,
    f.chart_type,
    f.country,
    f.track_id,
    f.rank,
    t.track_name,
    t.features_found,
    t.energy,
    t.valence
FROM music.fact_chart AS f
LEFT JOIN music.dim_track AS t ON t.track_id = f.track_id
/*__WHERE__*/
ORDER BY f.rank;
