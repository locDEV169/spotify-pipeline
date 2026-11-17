-- Spotify pipeline music schema (SPEC + field notes 2026-11-17)
-- Scope: CREATE SCHEMA music + music.* only.
-- NEVER touch public.weather_* (or any weather objects).

CREATE SCHEMA IF NOT EXISTS music;

-- ===== Bronze (jsonb) =====
CREATE TABLE IF NOT EXISTS music.raw_charts (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id        text,
    source        text NOT NULL,
    chart_date    date,
    chart_type    text,
    country       text,
    payload       jsonb NOT NULL,
    ingested_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS music.raw_spotify (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id        text,
    source        text,
    entity        text NOT NULL,
    spotify_id    text,
    payload       jsonb NOT NULL,
    ingested_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS music.raw_reccobeats (
    id                 bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id             text,
    source             text,
    endpoint           text NOT NULL,
    spotify_track_ids  text[],
    payload            jsonb NOT NULL,
    ingested_at        timestamptz NOT NULL DEFAULT now()
);

-- ===== Silver =====
CREATE TABLE IF NOT EXISTS music.fact_chart (
    chart_date            date NOT NULL,
    chart_type            text NOT NULL,
    country               text NOT NULL,
    track_id              text NOT NULL,
    rank                  integer NOT NULL CHECK (rank >= 1),
    prev_rank             integer CHECK (prev_rank IS NULL OR prev_rank >= 1),
    streams               bigint CHECK (streams IS NULL OR streams >= 0),
    entry_status          text,
    peak_rank             integer,
    appearances_on_chart  integer,
    run_id                text,
    source                text,
    ingested_at           timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (chart_date, chart_type, country, track_id)
);

CREATE TABLE IF NOT EXISTS music.dim_track (
    track_id                   text PRIMARY KEY,
    track_name                 text,
    duration_ms                integer,
    explicit                   boolean,
    album_id                   text,
    album_name                 text,
    release_date               text,
    release_date_precision     text,
    isrc                       text,
    track_popularity           integer,
    reccobeats_uuid            text,
    href                       text,
    acousticness               double precision,
    danceability               double precision,
    energy                     double precision,
    instrumentalness           double precision,
    liveness                   double precision,
    speechiness                double precision,
    valence                    double precision,
    loudness                   double precision,
    tempo                      double precision,
    key                        integer,
    mode                       integer,
    features_found             boolean NOT NULL DEFAULT false,
    features_fetched_at        timestamptz,
    source_features            text,
    run_id                     text,
    source                     text,
    updated_at                 timestamptz
);

CREATE TABLE IF NOT EXISTS music.dim_artist (
    artist_id           text PRIMARY KEY,
    artist_name         text,
    genres              jsonb,
    followers           bigint,
    artist_popularity   integer,
    run_id              text,
    source              text,
    updated_at          timestamptz
);

CREATE TABLE IF NOT EXISTS music.bridge_track_artist (
    track_id          text NOT NULL REFERENCES music.dim_track (track_id),
    artist_id         text NOT NULL REFERENCES music.dim_artist (artist_id),
    artist_position   integer NOT NULL DEFAULT 0,
    PRIMARY KEY (track_id, artist_id)
);

CREATE INDEX IF NOT EXISTS idx_fact_chart_track_id
    ON music.fact_chart (track_id);
CREATE INDEX IF NOT EXISTS idx_fact_chart_rank
    ON music.fact_chart (chart_date, chart_type, country, rank);
CREATE INDEX IF NOT EXISTS idx_dim_track_isrc
    ON music.dim_track (isrc);
CREATE INDEX IF NOT EXISTS idx_bridge_track_artist_artist_id
    ON music.bridge_track_artist (artist_id);

-- ===== Gold views =====
CREATE OR REPLACE VIEW music.gold_feature_coverage AS
SELECT
    f.chart_date,
    f.chart_type,
    f.country,
    count(*) AS chart_rows,
    count(*) FILTER (WHERE t.features_found) AS features_found_rows,
    round(
        100.0 * count(*) FILTER (WHERE t.features_found) / nullif(count(*), 0),
        2
    ) AS features_found_pct
FROM music.fact_chart AS f
LEFT JOIN music.dim_track AS t ON t.track_id = f.track_id
GROUP BY f.chart_date, f.chart_type, f.country;

CREATE OR REPLACE VIEW music.gold_movers AS
SELECT
    f.chart_date,
    f.chart_type,
    f.country,
    f.track_id,
    t.track_name,
    f.rank,
    f.prev_rank,
    (f.prev_rank - f.rank) AS rank_delta,
    f.streams
FROM music.fact_chart AS f
LEFT JOIN music.dim_track AS t ON t.track_id = f.track_id
WHERE f.prev_rank IS NOT NULL;

CREATE OR REPLACE VIEW music.gold_mood_segments AS
SELECT
    f.chart_date,
    f.chart_type,
    f.country,
    f.track_id,
    t.track_name,
    t.energy,
    t.valence,
    t.tempo,
    t.source_features
FROM music.fact_chart AS f
INNER JOIN music.dim_track AS t ON t.track_id = f.track_id
WHERE t.features_found IS TRUE;
