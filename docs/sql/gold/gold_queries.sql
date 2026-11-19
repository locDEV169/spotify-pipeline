-- Runtime Gold query templates (G1–G4). NOT DDL — VIEWs live in music_schema.sql.
-- Python: spotify_pipeline.pipeline.gold.sql
-- Placeholders (tokens only at real inject sites — never in comments): WHERE / BASE_JOIN / LIMIT
-- Missing path composes Silver LEFT JOIN (do not duplicate BR-6 join body here).
-- G2 movers: VIEW already filters prev_rank IS NOT NULL (GQ-2); streams may be NULL (GQ-9).
-- G3 mood: VIEW INNER JOIN + features_found IS TRUE (intentional; not a BR-6 chart drop).
-- G4 popularity: ad-hoc JOIN (no VIEW); Open Q2 / GQ-4 — often all-null on Dev Mode → skip in Python.

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

-- @@query: movers
-- VIEW music.gold_movers excludes prev_rank IS NULL (GQ-2 MVP — no new/re-entry).
SELECT chart_date, chart_type, country,
       track_id, track_name,
       rank, prev_rank, rank_delta, streams
FROM music.gold_movers
/*__WHERE__*/

-- @@query: mood_segments
-- VIEW music.gold_mood_segments: INNER JOIN + features_found IS TRUE (≠ BR-6).
SELECT chart_date, chart_type, country,
       track_id, track_name,
       energy, valence, tempo, source_features
FROM music.gold_mood_segments
/*__WHERE__*/

-- @@query: popularity_feature_pairs
-- Assumption: pair track_popularity with energy/valence/danceability (not a full matrix).
-- WHERE inject (alias f) then AND filters keep only usable pairs.
SELECT f.rank, f.track_id, t.track_name,
       t.track_popularity, t.energy, t.valence, t.danceability
FROM music.fact_chart AS f
LEFT JOIN music.dim_track AS t ON t.track_id = f.track_id
/*__WHERE__*/
  AND t.track_popularity IS NOT NULL
  AND (
    t.energy IS NOT NULL
    OR t.valence IS NOT NULL
    OR t.danceability IS NOT NULL
  )
ORDER BY f.rank
