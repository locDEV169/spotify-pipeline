-- Runtime Gold query templates (G1). NOT DDL — VIEWs live in music_schema.sql.
-- Python: spotify_pipeline.pipeline.gold
-- Placeholders: /*__WHERE__*/ /*__BASE_JOIN__*/ /*__LIMIT__*/
-- Missing path composes Silver LEFT JOIN (do not duplicate BR-6 join body here).
-- G2/G3 sections TBD.

-- @@query: feature_coverage
SELECT chart_date, chart_type, country,
       chart_rows, features_found_rows, features_found_pct
FROM music.gold_feature_coverage
/*__WHERE__*/

-- @@query: missing_features
SELECT rank, track_id, track_name, features_found
FROM (
/*__BASE_JOIN__*/
) AS j
WHERE features_found IS NOT TRUE
ORDER BY rank
LIMIT /*__LIMIT__*/
