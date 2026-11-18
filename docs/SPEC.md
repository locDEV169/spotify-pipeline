# Spec: Spotify Charts → Web API → ReccoBeats Pipeline (Demo)

**Status:** Draft for implementation (awaiting tool confirmations marked ⚠️)  
**Source research:** [Research – Spotify data sources & ReccoBeats pipeline (demo)](https://app.notion.com/p/Research-Spotify-data-sources-ReccoBeats-pipeline-demo-41a88b8696fa81049c9df55c450ae2d2) (16/11/2026, Asia/Bangkok)  
**Repo:** `spotify-data-pipeline` (greenfield)  
**Audience:** Learning / portfolio demo — not legal advice, not production SaaS

---

## Objective

Build a local **batch data pipeline** that:

1. Ingests Spotify chart rankings (grain: date × chart type × country × track).
2. Enriches track/artist metadata via **Spotify Web API** (Client Credentials) — **without** using locked audio-features endpoints.
3. Enriches audio-feature metrics via **ReccoBeats**.
4. Lands data in a **Bronze → Silver → Gold** (medallion) layout.
5. Supports analytics that degrade gracefully when features / popularity / genres are missing.

**Why:** New Spotify apps cannot use Audio Features / Audio Analysis ([Spotify blog 27/11/2024](https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api)). ReccoBeats provides proprietary substitutes ([ToS](https://reccobeats.com/docs/documentation/terms-of-service), [audio-features API](https://reccobeats.com/docs/apis/get-audio-features)).

**Success looks like:** One CLI command ingests a chart window, stores raw + curated tables, produces a short Gold report (movers / mood) with explicit `features_found` coverage stats.

---

## Locked decisions (from research §8 — 16/11/2026)

| Source | Role |
|--------|------|
| **Spotify Charts** (`charts-spotify-com-service`) | Ranking grain: `chart_date`, `chart_type`, `country`, rank, (streams if available) |
| **Spotify Web API** | Official metadata (track / artist / album fields still available) |
| **ReccoBeats** | Audio features only (`danceability`, `energy`, `valence`, `tempo`, …) |

**Not on the locked happy path:** kworb, Last.fm, Kaggle 1.2M, Deezer.  
They remain **documented fallbacks** (research §2, §4, §6 v1) if Charts `auth/v0` is unavailable or historical backfill is needed.

> Research §6 (kworb-primary) is an **older proposal**. Implementation follows **§8 / pipeline v2**.

---

## Assumptions I'm making (correct me if wrong)

1. **Language:** Python 3.12+ (matches DE learning path).
2. **MVP chart source:** Charts `public/v0` weekly Global top 50 (unauthenticated) — `streams = NULL`.
3. **Daily Top 200 + streams (`auth/v0`):** out of MVP until Bearer-user access and ToS acceptance are confirmed ⚠️.
4. **Storage MVP:** local filesystem Bronze (JSON/JSONL) + **SQLite** Silver/Gold.
   - **Runtime override (18/11/2026):** Bronze store of record = Postgres `music.raw_*` (jsonb + `ingested_at`). C8 = `pipeline/bronze.py` writers. Local `data/bronze/` = optional dual-write JSON envelope (Assumptions #4) — không thay SoR.
5. **Orchestration MVP:** CLI (+ optional OS cron later). No Airflow/Prefect yet ⚠️.
6. **Secrets:** `.env` locally; never commit. Secret-store product TBD ⚠️.
7. **BI:** deferred; Gold queries printable via CLI / optional notebook ⚠️.
8. **Spotify app mode:** implement **both** batch `?ids=` and single `/{id}` paths; detect which works on the configured Client ID ⚠️.
9. **Scope country:** Global first; multi-country later.

---

## Tech Stack

| Layer | Choice (MVP) |
|-------|----------------|
| Language | Python 3.12+ |
| HTTP | `httpx` |
| Config | `pydantic-settings` + `.env` |
| Storage | `pathlib` Bronze files + SQLite |
| CLI | `typer` or `argparse` |
| Tests | `pytest` + recorded fixtures (no live network in CI) |
| Packaging | `uv` or `pip` + `pyproject.toml` |

---

## Commands

```bash
# Setup
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
pip install -e ".[dev]"

# Run full pipeline for one watermark
python -m spotify_pipeline run \
  --chart-date 2026-11-12 \
  --chart-type weekly_top_songs \
  --country global

# Stages (optional)
python -m spotify_pipeline ingest-charts ...
python -m spotify_pipeline enrich-spotify ...
python -m spotify_pipeline enrich-reccobeats ...
python -m spotify_pipeline build-silver ...
python -m spotify_pipeline build-gold ...
python -m spotify_pipeline backfill-features

# Offline / fixture mode
python -m spotify_pipeline run --offline

# Tests
pytest -q
```

---

## Project Structure

Hybrid layout: keep package `src/spotify_pipeline/` (SPEC), but **tách riêng** theo vai trò từ Notion §9 — clients / models / pipeline / state / analytics không lẫn nhau.

### Layer responsibilities (tách riêng)

| Layer | Được làm | Không làm |
|-------|----------|-----------|
| `clients/` | HTTP I/O tới Charts / Spotify / ReccoBeats; retry 429 | Validate business row; Gold math |
| `models/` | Pydantic fail-fast sau extract (Optional popularity/genres/…) | Movers / mood / SCD2 |
| `pipeline/` | Ingest → enrich → bronze → silver → gold → backfill | Format Telegram/report UI |
| `state/` | Watermark `(chart_date, chart_type, country)` | Gọi API |
| `analytics/` | Đọc Gold → summary / movers / mood report | Copy logic SQL; gọi lại API |
| `scripts/` | Smoke-check local (Spotify / ReccoBeats) | Cloud Run / BQ deploy (hoãn) |

### Tree

```text
spotify-data-pipeline/
  docs/
    SPEC.md
  architecture/
    music-pipeline.png / .drawio / .drawio.zip
  src/spotify_pipeline/
    __init__.py
    cli.py                      # run / backfill / --report / --offline
    config/                     # .env + settings (batch sizes, paths)
      __init__.py
      config.py
    db/                         # server-side Supabase / Postgres
      __init__.py
      connection.py             # create_client (URL + service_role)
      postgres.py               # pg8000 + SUPABASE_DB_URL
    clients/                    # ← I/O only (tách riêng)
      __init__.py
      http.py                   # shared session, retry / Retry-After
      charts.py                 # public/v0 (+ stub auth/v0)
      spotify_auth.py           # Client Credentials, token ~1h
      spotify.py                # tracks/artists; batch hoặc /{id}
      reccobeats.py             # GET /v1/audio-features?ids= ≤40
    models/                     # ← validate only (tách riêng)
      __init__.py
      chart.py                  # ChartEntry (streams Optional)
      track.py                  # Track, Artist (deprecated fields Optional)
      audio_features.py         # AudioFeatures + features_found
    pipeline/                   # ← orchestration / medallion (tách riêng)
      __init__.py
      ingest_charts.py
      enrich_spotify.py
      enrich_reccobeats.py
      bronze.py
      silver.py
      gold.py
      backfill.py
      run.py                    # 1 cycle: watermark → … → summary
    state/                      # ← watermark only (tách riêng)
      __init__.py
      watermark.py
    analytics/                  # ← read Gold + present (tách riêng)
      __init__.py
      movers.py
      mood.py
      summary.py
  data/
    bronze/                     # gitignored raw JSON
    silver/                     # sqlite / curated
    gold/
  scripts/                      # local smoke only (cloud scripts deferred)
    check/                      # check_spotify / check_supabase / …
    bronze/                     # load_raw_* / clear_raw_*
    ddl/                        # apply_music_ddl
    auth/                       # spotify_login
  tests/
    fixtures/
      charts_public_v0_weekly.json
      tracks_batch.json
      tracks_single.json
      artists_batch.json
      reccobeats_audio_features.json   # 26/40-style
      reccobeats_batch41_error.json    # status 4004
    test_http_retry.py
    test_reccobeats_batch.py
    test_charts_parse.py
    test_models.py
    test_silver_left_join.py
    test_watermark.py
    test_analytics_summary.py
  .env.example
  .gitignore
  pyproject.toml
  README.md
```

**Hoãn (Notion §9 cloud — không đưa vào cây MVP):** `Dockerfile`, Cloud Run, GCS/BigQuery load, `staging/` NDJSON primary, Telegram alert, rename repo → `spotify-chart-elt/`.

---

## Architecture (pipeline v2)

Primary diagram (locked stack §8 / former Notion `music-pipeline-v2`):

| File | Meaning |
|------|---------|
| [`architecture/music-pipeline.png`](../architecture/music-pipeline.png) | Pipeline diagram |
| [`architecture/music-pipeline.drawio`](../architecture/music-pipeline.drawio) | Editable draw.io source |
| [`architecture/music-pipeline.drawio.zip`](../architecture/music-pipeline.drawio.zip) | Zipped source (Notion export) |

```mermaid
flowchart LR
  PUB["Charts public/v0\nweekly Global top50\ntrackUri, no streams"]
  AUTH["Charts auth/v0 daily\nTop200 + streams\n⚠️ confirm"]
  ORCH["Scheduler / CLI\nwatermark =\nchart_date + chart_type + country"]
  SEC["Secrets\nSpotify Client ID/Secret"]
  BR["Bronze\nraw Charts / Web API / ReccoBeats JSON\ningested_at"]
  EX["Extract Spotify track/artist IDs"]
  SP["Spotify Web API\nClient Credentials\nNO audio-features"]
  RB["ReccoBeats\nGET /v1/audio-features?ids=\nbatch ≤ 40\nretry 429"]
  FACT["fact_chart"]
  DIMT["dim_track\n+ features_found"]
  DIMA["dim_artist"]
  JOIN["LEFT JOIN"]
  GOLD["Gold\nmovers, SCD2, mood"]
  BI["BI ⚠️ TBD"]

  PUB --> ORCH
  AUTH -.-> ORCH
  ORCH --> BR
  SEC -.-> SP
  BR --> EX
  EX --> SP
  EX --> RB
  EX --> FACT
  SP --> DIMT
  SP --> DIMA
  RB --> DIMT
  SP --> BR
  RB --> BR
  FACT --> JOIN
  DIMT --> JOIN
  DIMA --> JOIN
  JOIN --> GOLD
  GOLD --> BI
  DIMT -.->|"features_found=false"| RB
```

**Watermark:** `(chart_date, chart_type, country)` — one pipeline run = one watermark.

---

## Component breakdown (implementable units)

| # | Component | Path (tách riêng) | Responsibility | Depends on |
|---|-----------|-------------------|----------------|------------|
| C1 | Config / secrets | `config/` | Load Spotify creds, paths, batch sizes | — |
| C2 | HTTP retry | `clients/http.py` | Shared session; 429 + Retry-After | C1 |
| C3 | Charts client | `clients/charts.py` | Fetch `public/v0`; parse `trackUri`, ranks | C2 |
| C4 | Spotify auth/client | `clients/spotify_auth.py`, `spotify.py` | Token ~1h; tracks/artists; batch hoặc `/{id}` | C2 |
| C5 | ReccoBeats client | `clients/reccobeats.py` | Batch ≤40 `?ids=`; map IDs; 429 | C2 |
| C6 | Models | `models/*` | Validate ChartEntry / Track / Artist / AudioFeatures | — |
| C7 | Watermark | `state/watermark.py` | `(chart_date, chart_type, country)` | C1 |
| C8 | Bronze writer | `pipeline/bronze.py` | Persist raw JSON + `ingested_at` | C3–C5 |
| C9 | Ingest / enrich | `pipeline/ingest_*.py`, `enrich_*.py` | Charts → validate → Bronze; Spotify/RB enrich | C3–C6, C8 |
| C10 | Silver builder | `pipeline/silver.py` | `fact_chart` + dims; **LEFT JOIN only** | C8, C9 |
| C11 | Gold builder | `pipeline/gold.py` | Movers, SCD2 (nice), mood (`features_found=true`) | C10 |
| C12 | Backfill | `pipeline/backfill.py` | Re-query ReccoBeats where `features_found=false` | C5, C10 |
| C13 | Analytics | `analytics/*` | Đọc Gold → report (`--report`); không gọi API | C11 |
| C14 | CLI / run | `cli.py`, `pipeline/run.py` | 1 cycle + exit codes + coverage % | all |
| C15 | Fixtures / offline | `tests/fixtures/` | E2E 26/40 + batch41; `run --offline` | C5–C13 |
| C16 | Tests | `tests/` | Retry, batching, LEFT JOIN, models, watermark | C2–C13 |

---

## Business rules (must implement)

1. **Never call** Spotify `/v1/audio-features`, `/v1/audio-analysis`, `/v1/recommendations`, or related-artists for this stack.
2. ReccoBeats metrics are **proprietary**, not Spotify Audio Features — label `source=reccobeats` everywhere.
3. ReccoBeats calls use **query `?ids=`** with Spotify track IDs. Do **not** put Spotify IDs in path `/:id` (returns 4041).
4. ReccoBeats batch size **≤ 40** (41+ → status `4004`). Dedupe IDs; preserve chart order for reconciliation.
5. Missing ReccoBeats tracks: omitted from `content[]` without failing the batch → set `features_found=false`, **keep chart row**.
6. Silver joins are **LEFT JOIN** — never drop chart rows for missing features / genres / popularity.
7. Honor HTTP **429 + `Retry-After`** for ReccoBeats (and Spotify).
8. Cache / persist raw ReccoBeats + Spotify payloads in Bronze (`ingested_at` required).
9. Do **not** use ReccoBeats search as coverage repair (E2E: wrong remix for chart #1).
10. Deprecated Spotify fields (`track.popularity`, `artist.genres`, `artist.followers`, `artist.popularity`) must be **nullable**; Gold degrades gracefully.
11. Learning/demo only: do not redistribute Spotify/Kaggle dumps; do not scrape `charts.spotify.com` for public/commercial portfolio without renewed ToS review.

---

## Data model (Silver)

### `fact_chart`
| Column | Source | Notes |
|--------|--------|-------|
| `chart_date` | Charts | Part of watermark |
| `chart_type` | Charts | e.g. `weekly_top_songs` |
| `country` | Charts | e.g. `global` |
| `track_id` | Charts `trackUri` | Spotify Base-62 |
| `rank` | `currentRank` | |
| `prev_rank` | `previousRank` | |
| `streams` | `auth/v0` only | NULL on `public/v0` |
| `entry_status` | Charts | optional |
| `ingested_at` | Pipeline | |

**PK / uniqueness:** `(chart_date, chart_type, country, track_id)`

### `dim_track`
| Column | Source | Notes |
|--------|--------|-------|
| `track_id` | Spotify / Charts | PK |
| `track_name`, `duration_ms`, `explicit` | Web API track | |
| `album_id`, `album_name`, `release_date`, `release_date_precision` | `track.album` | No separate `/albums` required for MVP |
| `isrc` | `external_ids.isrc` | Available per Mar 2026 revert |
| `track_popularity` | Web API | Nullable / deprecated |
| `reccobeats_uuid`, `href` | ReccoBeats | |
| Audio feature columns | ReccoBeats | acousticness … valence |
| `features_found` | Pipeline | bool |
| `features_fetched_at` | Pipeline | |
| `source_features` | const `reccobeats` | |

### `dim_artist`
| Column | Source | Notes |
|--------|--------|-------|
| `artist_id` | Web API | PK |
| `artist_name` | Web API | |
| `genres` | `artist.genres` | Deprecated; may be empty |
| `followers` | `followers.total` | May be absent on new Dev Mode |
| `artist_popularity` | Web API | May be absent on new Dev Mode |

---

## API contracts (implementation constraints)

### Spotify
- Auth: `POST https://accounts.spotify.com/api/token` (`client_credentials`), token ~3600s.
- Prefer `GET /v1/tracks?ids=` (max 50) / `GET /v1/artists?ids=` (max 50) when Client ID still allows batch.
- Fallback: `GET /v1/tracks/{id}`, `GET /v1/artists/{id}` for new Dev Mode (post 11/02/2026 limits).
- Albums: use embedded `track.album`; optional `GET /v1/albums/{id}` only if needed.

### ReccoBeats
- Base: `https://api.reccobeats.com`
- Header: `Accept: application/json`
- No API key
- Primary: `GET /v1/audio-features?ids=id1,id2,...` (≤40)
- Optional metadata: `GET /v1/track?ids=...` (≤40)
- On 429: sleep `Retry-After`, retry with capped attempts

### Charts
- MVP: unofficial `public/v0` weekly Top Songs Global (top 50) — no streams.
- ⚠️ `auth/v0` daily Top 200 + streams: confirm Bearer user token lifetime + ToS acceptance before coding.

---

## E2E evidence to encode as fixtures (16/11/2026)

- Sample: 40 weekly Global track IDs → ReccoBeats **26/40** matched on both audio-features and track metadata.
- Top **#1–#6 missing** (new releases lag) — pipeline must keep those ranks with `features_found=false`.
- Matched example: The Killers – Mr. Brightside (`003vvx7Niy0yvhvHt4a68B`) with full feature payload (see research §5).

---

## Gold analytics (MVP)

1. **Coverage report:** `% features_found`, list of missing top-N ranks.
2. **Movers:** rank delta (`prev_rank - rank`) for watermark.
3. **Mood segments:** only rows with `features_found=true` (e.g. energy×valence quadrants) — document thresholds in code comments.
4. **Optional:** popularity vs features scatter — skip/null-safe if `track_popularity` absent.

SCD2 rank history: MVP may store append-only `fact_chart` and compute history by query; formal SCD2 table is nice-to-have.

---

## Code Style

```python
# Good: chunk + preserve order + never fail whole batch on partial misses
def chunked(ids: list[str], size: int = 40) -> list[list[str]]:
    uniq = list(dict.fromkeys(ids))  # dedupe, keep order
    return [uniq[i : i + size] for i in range(0, len(uniq), size)]
```

- Prefer explicit functions over class hierarchies.
- Network I/O only inside `clients/`.
- Pure transforms in `pipeline/` / `analytics/`.
- Type hints on public functions; fail fast on invalid watermark.

---

## Testing Strategy

| Level | What |
|-------|------|
| Unit | ID chunking (41 → 4004 prevention), URI parse, LEFT JOIN semantics |
| Contract | ReccoBeats/Spotify fixture JSON → model mapping |
| Integration (optional local) | Live smoke behind `@pytest.mark.live` |
| Regression | Offline `run --offline` reproduces summary counts from fixtures |

CI: offline tests only.

---

## Boundaries

**Always**
- Persist Bronze raw payloads before Silver transforms.
- LEFT JOIN chart ↔ features.
- Label ReccoBeats provenance.
- Keep secrets out of git.
- Document ToS / unofficial Charts risk in README.

**Ask first**
- Enabling `auth/v0` or kworb HTML scraping.
- Adding cloud warehouse / Airflow / public dashboard.
- Publishing dataset dumps.
- Changing locked stack away from Charts + Web API + ReccoBeats.

**Never**
- Call Spotify audio-features / audio-analysis for this project.
- Use ReccoBeats path endpoints with Spotify IDs.
- Drop chart rows when enrichment misses.
- Claim ReccoBeats numbers equal Spotify Audio Features.
- Commit `.env` or access tokens.

---

## Implementation order

1. Scaffold `pyproject.toml`, config, `.env.example`, folder layout.
2. ReccoBeats client + fixtures from §5 E2E (highest risk learning).
3. Charts `public/v0` ingest → Bronze.
4. Spotify Client Credentials + track/artist enrich → Bronze.
5. Silver tables + LEFT JOIN + `features_found`.
6. Gold summary (coverage + movers + mood).
7. Backfill job.
8. CLI `run` + README (architecture, risks, how to run offline).
9. Optional: auth/v0, BI, scheduler — after ⚠️ checklist below.

---

## Success Criteria

- [ ] `run --offline` completes Bronze→Silver→Gold using fixtures.
- [ ] Live `run` for one weekly Global watermark stores chart rows for **all** returned ranks.
- [ ] ReccoBeats enrichment never exceeds 40 IDs/request.
- [ ] Missing ReccoBeats tracks yield `features_found=false` without dropping `fact_chart` rows.
- [ ] No Spotify audio-features calls in codebase.
- [ ] Deprecated Spotify fields nullable; Gold still runs.
- [ ] README states ReccoBeats AS-IS risk, Charts unofficial/`public/v0` risk, and learning-only scope.
- [ ] `.env.example` documents `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET`; no secrets committed.
- [ ] Pytest offline suite green.

---

## Open Questions (blocking / high impact)

1. Spotify Client ID mode: Extended Quota vs Dev Mode old vs Dev Mode new? → batch vs `/{id}`.
2. On that Client ID, are `track.popularity`, `artist.genres`, `followers`, `artist.popularity` still returned? → **Answered for current Dev Mode app (field notes 17/11/2026):** absent / always null on this Client ID; Gold popularity scatter **not feasible** here. Other quota modes still ⚠️.
3. Accept Charts `auth/v0` daily (Bearer user) for streams despite ToS risk, or stay weekly `public/v0` + `streams=NULL`?
4. If no `auth/v0`: stay weekly-only, or revive kworb fallback?
5. Scheduler / secret store / object store / BI product choices.
6. Measured rate-limit thresholds (ReccoBeats + Spotify) — unknown; implement defensive retries.
7. Does the Spotify app owner have Premium (required for current Dev Mode)?

---

## Risks (carry into README)

| Risk | Severity | Mitigation |
|------|----------|------------|
| ReccoBeats coverage gaps (E2E 26/40; top ranks missing) | High | LEFT JOIN + backfill + coverage report |
| ReccoBeats AS-IS / shutdown | High | Bronze cache + offline fixtures |
| Charts unofficial + ToS scrape ban | High | Prefer documented learning scope; avoid public scrape of charts.spotify.com |
| Spotify Dev Mode field/endpoint removals | Medium | Single-ID fallback; nullable fields |
| Rate limits unpublished | Medium | Retry-After, low concurrency, cache |
| Feature fidelity ≠ historical Spotify/Kaggle | Medium | Never claim parity; optional later comparison study |

---

## Change log

| Date | Change |
|------|--------|
| 2026-11-16 | Initial SPEC distilled from Notion research §1–§8 + BA component mapping. Locked stack = Charts + Web API + ReccoBeats (v2). |
| 2026-11-17 | Bổ sung mục "Lưu trữ bằng Supabase" (đề xuất của mình, 17/11/2026, Asia/Bangkok). Các mục phía trên không bị sửa hay xóa. |
| 2026-11-17 | Field notes: live probe Charts / Web API / ReccoBeats; trạng thái schema Supabase (chỉ weather); DDL deltas (`run_id`/`source`, indexes); config Supabase đã có trong code. **Không** chạy DDL; **không** đụng bảng weather. |
| 2026-11-17 | Quyết định: bảng nhạc nằm schema Postgres **`music`** (tách khỏi weather/`public`). Chỉ sync `docs/SPEC.md` (không Notion). DDL vẫn **chưa chạy**. |
| 2026-11-17 | Thêm `docs/sql/music_schema.sql` + `scripts/ddl/apply_music_ddl.py` (schema `music.*`, không đụng weather). Apply cần `SUPABASE_DB_URL` — **chưa apply** nếu URI chưa có trong `.env`. |
| 2026-11-17 | **DDL applied** trên Supabase schema `music` (10 objects: raw_*/fact_chart/dim_*/bridge/gold_*). Weather `public` giữ nguyên. Script migrate: `python scripts/ddl/apply_music_ddl.py`. |

---

## Lưu trữ bằng Supabase (đề xuất của mình)

> **Đề xuất của mình** — 17/11/2026 (Asia/Bangkok). Mục này được **append** vào cuối file; không sửa các mục phía trên (kể cả Assumptions #4: Bronze local filesystem + SQLite Silver/Gold vẫn là MVP đã viết). Đây là phương án lưu trữ thay thế / bổ sung, **chưa triển khai**. Các trường và tên bảng dưới đây bám [Data model (Silver)](#data-model-silver) và [Gold analytics (MVP)](#gold-analytics-mvp) đã có trong file này.

### Vì sao dùng Supabase

Supabase là Postgres được quản lý, kèm **Storage** để chứa file. Phù hợp pipeline demo này vì lượng dữ liệu nhỏ: Charts `public/v0` weekly Global top 50 chỉ khoảng **50 hàng/tuần**, cộng metadata Web API và audio features ReccoBeats thì chỉ cỡ vài MB — nằm trong hạn mức gói Free (xem mục giới hạn bên dưới, đã đối chiếu docs).

Có thể dùng connection string Postgres (SQL thuần, upsert, view) cho Silver/Gold, và dùng Storage cho JSON thô ở Bronze, cùng một project.

### Ánh xạ lớp Medallion

| Lớp | Cách lưu trên Supabase (đề xuất của mình) | Ghi chú |
|-----|-------------------------------------------|---------|
| **Bronze** | (A) bucket Storage, path theo nguồn/ngày; hoặc (B) bảng `raw_*` với cột `jsonb` + `ingested_at` | Giữ payload thô Charts / Web API / ReccoBeats. Không làm sạch nghiệp vụ ở lớp này. |
| **Silver** | Bảng Postgres: `fact_chart`, `dim_track`, `dim_artist` (đúng tên trong Data model ở trên) | Upsert idempotent (`ON CONFLICT`). Join Silver vẫn là **LEFT JOIN** — không drop hàng chart khi thiếu feature / genre / popularity. |
| **Gold** | `VIEW` hoặc `MATERIALIZED VIEW` | Coverage, movers, mood; SCD2 formal là nice-to-have (có thể tính từ `fact_chart` append-only). |

**Path Bronze trên Storage (đề xuất của mình, không có trong file gốc):**

```text
bronze/charts/public_v0/chart_date={YYYY-MM-DD}/{country}_{chart_type}.json
bronze/spotify/tracks/{YYYY-MM-DD}/{track_id}.json
bronze/spotify/artists/{YYYY-MM-DD}/{artist_id}.json
bronze/reccobeats/audio-features/{YYYY-MM-DD}/{batch_or_track_id}.json
```

Mọi object / hàng raw đều có `ingested_at`. Có thể dùng **cả hai** (A) và (B): file trên Storage là bản gốc, bảng `raw_*` tiện truy vấn.

### DDL đề xuất (Silver + raw + Gold)

Chỉ gồm trường **đang có trong Data model / API contracts** của file này: Charts `public/v0` có `rank` (`currentRank`), `prev_rank` (`previousRank`), `trackUri` → `track_id`, `chart_date` — **không có số streams** (`streams` để NULL). Web API Dev Mode (Feb 2026): `track_popularity`, `followers`, `artist_popularity` **nullable** (có thể absent). `isrc` vẫn dùng được (reverted 03/2026). Audio features lấy từ ReccoBeats, gắn `source_features = 'reccobeats'`.

```sql
-- ===== Bronze (phương án B: jsonb) — đề xuất của mình =====
CREATE TABLE IF NOT EXISTS raw_charts (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source        text NOT NULL,          -- ví dụ: charts_public_v0
    chart_date    date,
    chart_type    text,
    country       text,
    payload       jsonb NOT NULL,
    ingested_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS raw_spotify (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entity        text NOT NULL,          -- track | artist
    spotify_id    text,
    payload       jsonb NOT NULL,
    ingested_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS raw_reccobeats (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    endpoint      text NOT NULL,          -- audio-features | track
    payload       jsonb NOT NULL,
    ingested_at   timestamptz NOT NULL DEFAULT now()
);

-- ===== Silver — bám Data model đã có =====
CREATE TABLE IF NOT EXISTS fact_chart (
    chart_date    date NOT NULL,
    chart_type    text NOT NULL,          -- ví dụ: weekly_top_songs
    country       text NOT NULL,          -- ví dụ: global
    track_id      text NOT NULL,          -- từ trackUri (spotify:track:{id})
    rank          integer NOT NULL CHECK (rank >= 1),
    prev_rank     integer CHECK (prev_rank >= 1),
    streams       bigint CHECK (streams >= 0),  -- NULL trên public/v0
    entry_status  text,
    ingested_at   timestamptz NOT NULL,
    PRIMARY KEY (chart_date, chart_type, country, track_id)
);

CREATE TABLE IF NOT EXISTS dim_track (
    track_id                   text PRIMARY KEY,
    track_name                 text,
    duration_ms                integer,
    explicit                   boolean,
    album_id                   text,
    album_name                 text,
    release_date               text,       -- giữ text vì có release_date_precision (year/month/day)
    release_date_precision     text,
    isrc                       text,
    track_popularity           integer,    -- nullable / có thể absent trên Dev Mode
    reccobeats_uuid            text,
    href                       text,
    acousticness               double precision,
    danceability               double precision,
    energy                     double precision,
    instrumentalness           double precision,
    liveness                   double precision,
    speechiness                double precision,
    valence                    double precision,
    loudness                   double precision,  -- dB, không buộc 0–1
    tempo                      double precision,
    key                        integer,
    mode                       integer,
    features_found             boolean NOT NULL DEFAULT false,
    features_fetched_at        timestamptz,
    source_features            text,       -- const 'reccobeats'
    updated_at                 timestamptz
);

CREATE TABLE IF NOT EXISTS dim_artist (
    artist_id           text PRIMARY KEY,
    artist_name         text,
    genres              jsonb,            -- deprecated; có thể rỗng / absent
    followers           bigint,           -- có thể absent trên Dev Mode mới
    artist_popularity   integer,          -- có thể absent trên Dev Mode mới
    updated_at          timestamptz
);

-- Bảng liên kết track–artist: đề xuất của mình, không có trong Data model gốc
-- (file gốc đã có dim_artist nhưng chưa ghi bảng nối).
CREATE TABLE IF NOT EXISTS bridge_track_artist (
    track_id          text NOT NULL REFERENCES dim_track (track_id),
    artist_id         text NOT NULL REFERENCES dim_artist (artist_id),
    artist_position   integer NOT NULL DEFAULT 0,
    PRIMARY KEY (track_id, artist_id)
);
```

**Upsert idempotent (đề xuất của mình):**

```sql
INSERT INTO fact_chart (
    chart_date, chart_type, country, track_id,
    rank, prev_rank, streams, entry_status, ingested_at
) VALUES (
    %(chart_date)s, %(chart_type)s, %(country)s, %(track_id)s,
    %(rank)s, %(prev_rank)s, %(streams)s, %(entry_status)s, now()
)
ON CONFLICT (chart_date, chart_type, country, track_id) DO UPDATE SET
    rank         = EXCLUDED.rank,
    prev_rank    = EXCLUDED.prev_rank,
    streams      = EXCLUDED.streams,
    entry_status = EXCLUDED.entry_status,
    ingested_at  = EXCLUDED.ingested_at;

INSERT INTO dim_track (
    track_id, track_name, duration_ms, explicit,
    album_id, album_name, release_date, release_date_precision,
    isrc, track_popularity, reccobeats_uuid, href,
    acousticness, danceability, energy, instrumentalness,
    liveness, speechiness, valence, loudness, tempo, key, mode,
    features_found, features_fetched_at, source_features, updated_at
) VALUES (
    %(track_id)s, %(track_name)s, %(duration_ms)s, %(explicit)s,
    %(album_id)s, %(album_name)s, %(release_date)s, %(release_date_precision)s,
    %(isrc)s, %(track_popularity)s, %(reccobeats_uuid)s, %(href)s,
    %(acousticness)s, %(danceability)s, %(energy)s, %(instrumentalness)s,
    %(liveness)s, %(speechiness)s, %(valence)s, %(loudness)s, %(tempo)s, %(key)s, %(mode)s,
    %(features_found)s, %(features_fetched_at)s, 'reccobeats', now()
)
ON CONFLICT (track_id) DO UPDATE SET
    track_name               = EXCLUDED.track_name,
    duration_ms              = EXCLUDED.duration_ms,
    explicit                 = EXCLUDED.explicit,
    album_id                 = EXCLUDED.album_id,
    album_name               = EXCLUDED.album_name,
    release_date             = EXCLUDED.release_date,
    release_date_precision   = EXCLUDED.release_date_precision,
    isrc                     = COALESCE(EXCLUDED.isrc, dim_track.isrc),
    track_popularity         = EXCLUDED.track_popularity,
    reccobeats_uuid          = COALESCE(EXCLUDED.reccobeats_uuid, dim_track.reccobeats_uuid),
    href                     = COALESCE(EXCLUDED.href, dim_track.href),
    acousticness             = COALESCE(EXCLUDED.acousticness, dim_track.acousticness),
    danceability             = COALESCE(EXCLUDED.danceability, dim_track.danceability),
    energy                   = COALESCE(EXCLUDED.energy, dim_track.energy),
    instrumentalness         = COALESCE(EXCLUDED.instrumentalness, dim_track.instrumentalness),
    liveness                 = COALESCE(EXCLUDED.liveness, dim_track.liveness),
    speechiness              = COALESCE(EXCLUDED.speechiness, dim_track.speechiness),
    valence                  = COALESCE(EXCLUDED.valence, dim_track.valence),
    loudness                 = COALESCE(EXCLUDED.loudness, dim_track.loudness),
    tempo                    = COALESCE(EXCLUDED.tempo, dim_track.tempo),
    key                      = COALESCE(EXCLUDED.key, dim_track.key),
    mode                     = COALESCE(EXCLUDED.mode, dim_track.mode),
    features_found           = EXCLUDED.features_found,
    features_fetched_at      = COALESCE(EXCLUDED.features_fetched_at, dim_track.features_fetched_at),
    source_features          = COALESCE(EXCLUDED.source_features, dim_track.source_features),
    updated_at               = EXCLUDED.updated_at;

INSERT INTO dim_artist (
    artist_id, artist_name, genres, followers, artist_popularity, updated_at
) VALUES (
    %(artist_id)s, %(artist_name)s, %(genres)s, %(followers)s, %(artist_popularity)s, now()
)
ON CONFLICT (artist_id) DO UPDATE SET
    artist_name         = EXCLUDED.artist_name,
    genres              = EXCLUDED.genres,
    followers           = EXCLUDED.followers,
    artist_popularity   = EXCLUDED.artist_popularity,
    updated_at          = EXCLUDED.updated_at;
```

`ON CONFLICT` của `dim_track` dùng `COALESCE` cho audio features / ISRC để lần upsert metadata (chưa có ReccoBeats) không ghi đè mất feature đã backfill, và ngược lại.

**Gold — view (đề xuất của mình), bám Gold analytics (MVP):**

```sql
CREATE OR REPLACE VIEW gold_feature_coverage AS
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
FROM fact_chart AS f
LEFT JOIN dim_track AS t ON t.track_id = f.track_id
GROUP BY f.chart_date, f.chart_type, f.country;

CREATE OR REPLACE VIEW gold_movers AS
SELECT
    f.chart_date,
    f.chart_type,
    f.country,
    f.track_id,
    t.track_name,
    f.rank,
    f.prev_rank,
    (f.prev_rank - f.rank) AS rank_delta,  -- dương = tăng hạng
    f.streams                              -- NULL trên public/v0
FROM fact_chart AS f
LEFT JOIN dim_track AS t ON t.track_id = f.track_id
WHERE f.prev_rank IS NOT NULL;

CREATE OR REPLACE VIEW gold_mood_segments AS
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
FROM fact_chart AS f
INNER JOIN dim_track AS t ON t.track_id = f.track_id
WHERE t.features_found IS TRUE;
-- Ngưỡng phân vùng energy × valence để trong comment code khi triển khai (SPEC: document thresholds in code comments).
```

Có thể đổi các view trên thành `MATERIALIZED VIEW` rồi `REFRESH` sau mỗi watermark nếu báo cáo đọc nhiều. SCD2 lịch sử hạng: MVP có thể query trực tiếp `fact_chart` (append-only theo watermark); bảng SCD2 formal vẫn là nice-to-have như mục Gold analytics.

### Cấu hình (`.env`)

**Đã có trong code (field notes 17/11/2026):** `Settings` trong `config.py` đọc `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_DB_URL`; `.env.example` đã document placeholders; `get_supabase_client()` + `scripts/check/check_supabase.py` dùng URL + service_role.

Thêm vào `.env` local, **không commit**, không dán key vào chat / SPEC:

```bash
# Cách 1 — kết nối thẳng Postgres (phù hợp psycopg) — optional
SUPABASE_DB_URL=postgresql://USER:PASSWORD@HOST:PORT/postgres

# Cách 2 — URL project + service_role (phù hợp supabase-py / Storage API) — đang dùng cho smoke
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

Dùng **một trong hai cách** (hoặc cả hai nếu vừa SQL vừa Storage API). Lấy giá trị từ Supabase Dashboard — không ghi giá trị thật vào repo.

**`SUPABASE_SERVICE_ROLE_KEY` chỉ dùng phía server/script.** Key này bỏ qua RLS; không đưa vào client, frontend, hay commit. Nếu key từng lộ trong chat: **rotate** trên Dashboard rồi cập nhật `.env` (backup cũ có thể nằm dưới `.backup-auth-20261117/`).

### Thư viện Python

| Lựa chọn | Trạng thái |
|----------|------------|
| `supabase` (`supabase-py`) | **Đã thêm** vào `pyproject.toml` — `create_client` / Storage / PostgREST. |
| `psycopg[binary]` | Chưa thêm — dùng khi nối thẳng `SUPABASE_DB_URL` để chạy DDL / upsert SQL thuần. |

### Giới hạn gói Free (đã đối chiếu docs, 17/11/2026)

Đã đọc [Supabase Pricing](https://supabase.com/pricing) và [Project Pausing](https://supabase.com/docs/guides/platform/free-project-pausing) ngày 17/11/2026:

| Hạng mục | Gói Free (theo docs trên) |
|----------|---------------------------|
| Giá | $0/tháng |
| Database | 500 MB / project |
| File Storage | 1 GB |
| Egress | 5 GB (kèm 5 GB cached egress) |
| Số project active | tối đa 2 |
| Tự tạm dừng | project Free bị pause sau **1 tuần không đủ hoạt động** (inactivity / low activity trong 7 ngày) |
| Khôi phục | Resume từ Dashboard; cửa sổ restore tối đa **1 năm** sau khi pause |
| Gói trả phí | không bị auto-pause vì inactivity |

Lượng data demo (≈ 50 hàng chart/tuần + metadata + features) thường nhỏ hơn 500 MB / 1 GB Storage rất nhiều. Nếu project bị pause: vào Dashboard, chọn project, bấm Resume. Docs ghi khoảng vài request/ngày tới database thường đủ để tránh pause — không phải bảo đảm tuyệt đối. Muốn không bị pause thì nâng lên gói trả phí.

### Việc cố ý chưa làm trong lần append này

- Không sửa Assumptions, Tech Stack, Data model gốc, hay cây thư mục phía trên (Assumptions #4 SQLite vẫn là MVP đã viết).
- **Chưa chạy DDL** tạo bảng nhạc trên Supabase; **không** đụng 3 bảng weather.
- Chưa đổi pipeline runtime từ SQLite/local Bronze sang Postgres/Storage làm store chính.

### Quan sát live — field notes (17/11/2026, Asia/Bangkok)

> Ghi nhận từ probe data thật + kiểm tra schema Supabase. **Không** coi là DDL đã apply.

#### Schema project hiện tại

| Object | Vai trò |
|--------|---------|
| `public.weather_snapshots`, `public.lifestyle_insights`, `public.current_weather` | Bảng thời tiết có sẵn — **không sửa / không drop** |
| Schema **`music`** (`music.fact_chart`, `music.dim_*`, …) | **Chưa tạo** — đây là chỗ dành cho pipeline nhạc |

**Decision (locked 17/11/2026):** tạo toàn bộ object nhạc trong schema **`music`**, cùng Supabase project nhưng **tách** khỏi weather/`public`. Không đặt `fact_chart` / `dim_*` vào `public`.

#### DDL là gì (trong ngữ cảnh repo này)?

**DDL** (*Data Definition Language*) = câu SQL **định nghĩa cấu trúc** DB, ví dụ:

- `CREATE SCHEMA` / `CREATE TABLE` / `CREATE INDEX` / `CREATE VIEW`

**Không** phải DDL (**DML**): `INSERT` / `UPDATE` / `SELECT` dữ liệu chart hay weather.

→ “Chưa chạy DDL” = mới ghi trong SPEC, **chưa** tạo schema/bảng/index thật trên Supabase. “Chạy DDL” = execute các `CREATE …` đó (vẫn **không** đụng bảng weather).

#### Charts `public/v0` (live)

| Có trong payload | Ghi chú thiết kế |
|------------------|------------------|
| `currentRank` → `rank` | Bắt buộc cho fact |
| `previousRank` → `prev_rank` | Nullable nếu thiếu |
| `entryStatus` → `entry_status` | Nullable |
| `trackUri` → `track_id` | Parse Base-62 |
| tên bài / nghệ sĩ (trên chart payload) | Có thể mirror vào dim; nguồn chuẩn metadata vẫn Web API |
| **Không có streams** | `streams` luôn NULL trên happy path `public/v0` |
| `peakRank`, `appearancesOnChart` | Có thể xuất hiện nhưng live = 0 / rỗng → cột **nullable**; **không** diễn giải `0` như peak thật |

#### Spotify Web API (Client ID hiện tại — Dev Mode)

| Có | Không có (để NULL) |
|----|---------------------|
| `name`, `duration_ms`, `explicit`, album (`id`/`name`/`release_date`/`precision`), `external_ids.isrc` | `track.popularity`, `artist.genres`, `followers`, `artist.popularity` |

→ Cột popularity / genres / followers vẫn giữ trong DDL nhưng **luôn trống** trên app này. Biểu đồ Gold “popularity vs features” **không làm được** cho đến khi Client ID khác trả field (vẫn ⚠️ Extended Quota).

#### ReccoBeats (live)

- Đủ **11** audio features (khớp cột `dim_track`).
- `id` trong response = **ReccoBeats UUID** (`reccobeats_uuid`), **không** phải Spotify track id.
- Nối dữ liệu: **luôn lưu Spotify track id đã request**; dùng `isrc` làm khóa phụ khi có. Không dựa vào ReccoBeats `id` như thể Spotify id.

### DDL deltas sau field notes (đề xuất — chưa chạy)

Áp dụng khi **tạo** object nhạc trên **cùng project**, schema **`music`**. Chỉ `CREATE … IF NOT EXISTS` — **cấm** `DROP`/`ALTER`/`TRUNCATE` mọi `public.weather_*`.

```sql
CREATE SCHEMA IF NOT EXISTS music;
```

Mọi bảng / view / index nhạc qualify `music.*` (ví dụ `music.fact_chart`, `music.dim_track`, `music.gold_movers`). Khi dùng supabase-py/PostgREST: expose schema `music` trong Dashboard API settings (ngoài `public`) nếu cần query qua client.

1. **Lineage:** thêm `run_id text` (hoặc `uuid`) + `source text` trên `music.raw_*` và (tuỳ chọn) `music.fact_chart` / `music.dim_track`.
2. **Charts extras (nullable):** `peak_rank`, `appearances_on_chart` — nullable; không diễn giải `0` như peak thật.
3. **`music.bridge_track_artist`:** giữ (một track nhiều artist).
4. **Indexes (đề xuất):**

```sql
CREATE INDEX IF NOT EXISTS idx_fact_chart_track_id ON music.fact_chart (track_id);
CREATE INDEX IF NOT EXISTS idx_fact_chart_rank ON music.fact_chart (chart_date, chart_type, country, rank);
CREATE INDEX IF NOT EXISTS idx_dim_track_isrc ON music.dim_track (isrc);
CREATE INDEX IF NOT EXISTS idx_bridge_track_artist_artist_id ON music.bridge_track_artist (artist_id);
```

5. **ReccoBeats raw:** `music.raw_reccobeats` nên có `spotify_track_ids text[]` (hoặc jsonb) = id đã gửi trong `?ids=`.

**Script apply (17/11/2026):**

| File | Vai trò |
|------|---------|
| [`docs/sql/music_schema.sql`](sql/music_schema.sql) | DDL đầy đủ: `CREATE SCHEMA music` + tables/indexes/views `music.*` (+ `run_id`/`source`, `peak_rank` nullable, `spotify_track_ids`, Gold views) |
| [`scripts/ddl/apply_music_ddl.py`](../scripts/ddl/apply_music_ddl.py) | Chạy SQL qua `SUPABASE_DB_URL` (`pg8000`); abort nếu SQL đụng weather |

```bash
# 1) Thêm SUPABASE_DB_URL vào .env (Dashboard → Database → Connect → URI)
# 2) Apply
python scripts/ddl/apply_music_ddl.py
# hoặc paste music_schema.sql vào Dashboard → SQL Editor → Run
```

**Trạng thái (17/11/2026):** `python scripts/ddl/apply_music_ddl.py` đã **exit 0** — schema `music` có 10 objects (`raw_charts`, `raw_spotify`, `raw_reccobeats`, `fact_chart`, `dim_track`, `dim_artist`, `bridge_track_artist`, `gold_feature_coverage`, `gold_movers`, `gold_mood_segments`). Weather `public` vẫn còn đủ 3 bảng. Idempotent: chạy lại script an toàn (`IF NOT EXISTS`). **Không** Notion. Rotate `service_role` vẫn do user trên Dashboard nếu key từng lộ.

> PostgREST/supabase-py: nếu query `music.*` qua API client, thêm schema `music` vào **Exposed schemas** trong Dashboard API settings.
