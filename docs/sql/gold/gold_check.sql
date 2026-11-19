-- Sample Gold SQL
-- Coverage VIEW (LEFT JOIN spirit — BR-6)
SELECT
    *
FROM
    music.gold_feature_coverage
WHERE
    chart_date = '2026-11-12'
    AND chart_type = 'weekly_top_songs'
    AND country = 'global';

-- Missing features (top ranks) — should include false/null features_found
SELECT
    f.rank,
    f.track_id,
    t.track_name,
    t.features_found
FROM
    music.fact_chart f
    LEFT JOIN music.dim_track t ON t.track_id = f.track_id
WHERE
    f.chart_date = '2026-11-12'
    AND f.chart_type = 'weekly_top_songs'
    AND f.country = 'global'
    AND t.features_found IS NOT TRUE
ORDER BY
    f.rank
LIMIT
    10;

-- Movers: prev_rank required; rank_delta = prev_rank - rank
SELECT
    count(*) AS movers,
    count(*) FILTER (
        WHERE
            streams IS NULL
    ) AS null_streams
FROM
    music.gold_movers
WHERE
    chart_date = '2026-11-12'
    AND chart_type = 'weekly_top_songs'
    AND country = 'global';

-- Mood ⊆ features_found (INNER JOIN filter ≠ BR-6)
SELECT
    count(*) AS mood_rows
FROM
    music.gold_mood_segments
WHERE
    chart_date = '2026-11-12'
    AND chart_type = 'weekly_top_songs'
    AND country = 'global';

-- Expect mood_rows ≤ features_found_rows; no features_found=false in this VIEW
-- Cross-check: no mood row with features_found false (should be 0)
SELECT
    count(*) AS bad_mood
FROM
    music.gold_mood_segments m
    JOIN music.dim_track t ON t.track_id = m.track_id
WHERE
    m.chart_date = '2026-11-12'
    AND m.chart_type = 'weekly_top_songs'
    AND m.country = 'global'
    AND t.features_found IS NOT TRUE;

-- Expect: bad_mood = 0
-- Movers chỉ có prev_rank
SELECT
    count(*)
FROM
    music.gold_movers
WHERE
    chart_date = '2026-11-12'
    AND chart_type = 'weekly_top_songs'
    AND country = 'global';