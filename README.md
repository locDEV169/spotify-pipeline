# Spotify Charts → Web API → ReccoBeats Pipeline

**Status:** Scaffold ready — package tree + CLI stubs (`NotImplementedError`). Pipeline logic not implemented yet.  
**Audience:** Learning / portfolio demo — not legal advice, not production SaaS.

Local **batch** data pipeline design that ingests Spotify chart rankings, enriches track/artist metadata via the Spotify Web API (Client Credentials), pulls audio-feature metrics from **ReccoBeats**, and lands data in a **Bronze → Silver → Gold** (medallion) layout.

> **Naming:** This folder is `spotify-pipeline`. The SPEC still refers to repo alias `spotify-data-pipeline` and Python package `spotify_pipeline` (planned).

## Why ReccoBeats?

New Spotify developer apps cannot use Audio Features / Audio Analysis ([Spotify blog, 27 Nov 2024](https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api)). ReccoBeats provides proprietary substitutes ([audio-features API](https://reccobeats.com/docs/apis/get-audio-features), [ToS](https://reccobeats.com/docs/documentation/terms-of-service)). Metrics are labeled `source=reccobeats` and are **not** claimed to equal historical Spotify Audio Features.

## Locked happy path

| Source | Role |
|--------|------|
| **Spotify Charts** (`charts-spotify-com-service`) | Ranking grain: `chart_date` × `chart_type` × `country` × track |
| **Spotify Web API** | Official track / artist / album metadata (no locked audio-features endpoints) |
| **ReccoBeats** | Audio features only (`danceability`, `energy`, `valence`, `tempo`, …) |

**Not** on the locked path (documented fallbacks only): kworb, Last.fm, Kaggle dumps, Deezer.

### Intended MVP (planned)

- Charts **`public/v0`** — weekly Global top 50 (unauthenticated); `streams = NULL`
- Enrichment → Bronze (raw JSON/JSONL) + **SQLite** Silver/Gold
- One CLI cycle per watermark `(chart_date, chart_type, country)`
- Gold summary: coverage (`features_found`), movers, mood (rows with features only)
- Offline mode from fixtures for CI (no live network)

Daily Top 200 + streams via Charts **`auth/v0`**, cloud warehouse, Airflow/Prefect, and BI dashboards are **out of MVP / undecided** (see [Open questions](#open-questions)).

## Architecture

![Pipeline diagram](architecture/music-pipeline.png)

Editable source: [`architecture/music-pipeline.drawio`](architecture/music-pipeline.drawio) · Full design: [`docs/SPEC.md`](docs/SPEC.md)

```text
Charts public/v0 ──► Bronze ──► extract IDs ──┬──► Spotify Web API ──► dim_track / dim_artist
                     ▲                         │
                     │                         └──► ReccoBeats (?ids= ≤40) ──► dim_track.features_*
                     │
                     └── raw JSON retained
                                              fact_chart ──► LEFT JOIN ──► Gold (movers / mood / coverage)
```

## Core rules

1. **Never** call Spotify `/v1/audio-features`, `/v1/audio-analysis`, `/v1/recommendations`, or related-artists.
2. ReccoBeats: query `GET /v1/audio-features?ids=` only — **not** Spotify IDs in path `/:id` (4041). Batch **≤ 40** IDs (41+ → `4004`).
3. Missing ReccoBeats tracks → `features_found=false`; **keep** the chart row (Silver uses **LEFT JOIN** only).
4. Do **not** use ReccoBeats search to “repair” coverage (wrong remix risk).
5. Deprecated Spotify fields (`popularity`, `genres`, `followers`, …) are nullable; Gold degrades gracefully.
6. Secrets live in `.env` only — never commit tokens.

## Observed ReccoBeats coverage (16/11/2026)

Sample of 40 weekly Global track IDs → **26/40** matched. Top ranks **#1–#6** were missing (new-release lag). The pipeline must retain those ranks with `features_found=false` and report coverage explicitly.

## Stack (scaffold)

| Layer | Choice |
|-------|--------|
| Language | Python 3.12+ |
| HTTP | `httpx` |
| Config | `pydantic-settings` + `.env` |
| Storage | filesystem Bronze + SQLite Silver/Gold (stdlib) |
| CLI | `typer` |
| Tests | `pytest` (+ recorded fixtures later) |
| Packaging | `pip` + `venv` + `pyproject.toml` |

Layout: `src/spotify_pipeline/` with separated `clients/`, `models/`, `pipeline/`, `state/`, `analytics/` (stubs raise `NotImplementedError` until implemented per SPEC).


## Scripts layout

| Folder | Scripts |
|--------|---------|
| `scripts/check/` | smoke probes (`check_spotify`, `check_spotify_user`, `check_supabase`, `check_reccobeats`) |
| `scripts/bronze/` | `load_raw_*` / `clear_raw_*` |
| `scripts/ddl/` | `apply_music_ddl` |
| `scripts/auth/` | `spotify_login` |

**Bronze store of record:** Postgres `music.raw_*` (jsonb + `ingested_at`) via `pipeline/bronze.py` (C8). Local filesystem `data/bronze/` (SPEC Assumptions #4) is deferred.

## Connect DB supabase
```bash
source .venv/bin/activate       # macOS / Linux
# source .venv/Scripts/activate # Windows Git Bash
python scripts/check/check_supabase.py
```

## Migrate music SQL → Supabase (schema `music` only)
```bash
# Requires SUPABASE_DB_URL in .env (Dashboard → Database → Connect)
python scripts/ddl/apply_music_ddl.py
python scripts/ddl/apply_music_ddl.py docs/sql/music_schema.sql   # optional path
```
Does **not** touch weather tables. Idempotent (`IF NOT EXISTS`).

## Bronze smoke: load / clear `music.raw_charts`
```bash
# Charts public/v0 → Weekly Top Songs + Top Artists (Global)
python scripts/bronze/load_raw_charts.py
python scripts/bronze/load_raw_charts.py --songs-only
python scripts/bronze/clear_raw_charts.py --run-id <run_id>
```

## Bronze smoke: load / clear `music.raw_spotify`
```bash
python scripts/bronze/load_raw_spotify.py                  # default: Charts top songs+artists
python scripts/bronze/load_raw_spotify.py <track_id> ...
# prints run_id — then:
python scripts/bronze/clear_raw_spotify.py --run-id <run_id>
python scripts/bronze/clear_raw_spotify.py --all --yes     # wipe table only
```

## Bronze smoke: load / clear `music.raw_reccobeats`
```bash
# ReccoBeats audio-features — default: Charts Weekly Global Top Songs (~50, chunked ≤40)
python scripts/bronze/load_raw_reccobeats.py
python scripts/bronze/load_raw_reccobeats.py 003vvx7Niy0yvhvHt4a68B
python scripts/bronze/clear_raw_reccobeats.py --run-id <run_id>
```

## Dev setup

```bash
python3 -m venv .venv           # or: python -m venv .venv
source .venv/bin/activate       # macOS / Linux
# source .venv/Scripts/activate # Windows Git Bash
pip install -e ".[dev]"
cp .env.example .env            # optional until live Spotify calls
pytest -q
```

Scaffold smoke tests should pass. Pipeline commands are registered but **not implemented** yet:

```bash
python -m spotify_pipeline run \
  --chart-date 2026-11-12 \
  --chart-type weekly_top_songs \
  --country global
# → NotImplementedError until C9–C14 are built
```

Env vars (see `.env.example`):

- `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET`
- `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` (server-only; never commit — rotate if leaked)

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| ReccoBeats coverage gaps (E2E 26/40; top ranks missing) | High | LEFT JOIN + backfill + coverage report |
| ReccoBeats AS-IS / possible shutdown | High | Bronze cache + offline fixtures |
| Charts unofficial + ToS scrape restrictions | High | Learning-only scope; no commercial scrape narrative |
| Spotify Dev Mode field/endpoint removals | Medium | Dual-path batch/`/{id}`; nullable fields |
| Unpublished rate limits | Medium | `Retry-After`, low concurrency, cache |
| Feature fidelity ≠ Spotify Audio Features / Kaggle | Medium | Never claim parity |

## Open questions

These are **undecided** — do not treat as product defaults:

1. Spotify Client ID mode (Extended Quota vs Dev Mode) → batch vs single-ID behavior
2. Whether `track.popularity` / `artist.genres` / `followers` / `artist.popularity` still return on that app
3. Charts `auth/v0` (daily + streams) vs stay on weekly `public/v0`
4. If no `auth/v0`: weekly-only forever, or revive a documented fallback (e.g. kworb)?
5. Scheduler / secret store / object store / BI product choices
6. Measured rate-limit thresholds (defensive retries only for now)
7. Whether the Spotify app owner has Premium (current Dev Mode requirement)

## Docs

| Path | Contents |
|------|----------|
| [`docs/SPEC.md`](docs/SPEC.md) | Full engineering spec (rules, data model, APIs, checklist) |
| [`docs/SPOTIFY_AUTH_TEST.md`](docs/SPOTIFY_AUTH_TEST.md) | Hướng dẫn test Spotify auth (Client Credentials + user login / refresh_token) |
| [`architecture/music-pipeline.drawio`](architecture/music-pipeline.drawio) | Editable pipeline diagram |
| [`architecture/music-pipeline.png`](architecture/music-pipeline.png) | Diagram export |

## Ask before changing

- Enabling Charts `auth/v0` or HTML scraping fallbacks
- Adding cloud warehouse / Airflow / public dashboard
- Publishing dataset dumps
- Leaving the locked stack (Charts + Web API + ReccoBeats)
