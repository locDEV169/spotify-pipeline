# Checklist: SPEC / diagram ↔ code gaps

**Purpose:** Working checklist để tick lệch, ghi quyết định Chubby, rồi update docs/code — không invent BR mới.  
**Source of truth:** [`docs/SPEC.md`](SPEC.md)  
**Last updated:** 2026-11-19  

### Files updated this pass (Gold C11 checklist §E)

| File | What changed |
|------|----------------|
| `docs/CHECKLIST_SPEC_GAPS.md` | **§E Gold C11 (G1–G7)** · §C Gold slice order · soft GQ-* |

### Prior pass (Silver C10 W1–W7 complete)

| File | What changed |
|------|----------------|
| `docs/CHECKLIST_SPEC_GAPS.md` | §D **W1–W7 [x]** · D04/C-5 closed · F7 capture |
| `src/spotify_pipeline/pipeline/silver.py` | W1–W6: builders + LEFT JOIN helper + `build_silver` |
| `src/spotify_pipeline/cli.py` | `build-silver` → `build_silver()` one-pass |
| `src/spotify_pipeline/models/*` | Chart/Track/Artist/AudioFeatures |
| `tests/test_silver_*.py` | W1–W6 unit tests (incl. LEFT JOIN / COALESCE) |
| `README.md` / `docs/SPEC.md` | Status + change log Silver C10 MVP |

### Prior pass (Q-D=2 + C1/C2 doc lock)

| File | What changed |
|------|----------------|
| `docs/CHECKLIST_SPEC_GAPS.md` | Q-C=1 · Q-D=2 · F5 skipped · D07/D10/D11 · DOC-1/2/5 · C-3 deferred |
| `docs/SPEC.md` | Assumption #4/#8 · Tech Stack Storage · C4 · Spotify API · Open Q1 · Change log · tree comment |
| `README.md` | Status · Intended MVP · Stack · Dev setup · Risks · Open Q1 |
| `src/spotify_pipeline/clients/spotify.py` | Module docstring align Q-D=2 |

---

> **Note (Fact):** Stage 4 enrich **đã tồn tại** (`enrich-spotify` / `enrich-reccobeats` → Bronze `raw_*`). Gaps dưới đây là **fidelity với sơ đồ/SPEC** (extract từ Bronze, parallel, `features_found` vào Silver, Stage 5+), không phải “chưa có enrich”.

---

## Legend

| Tag | Meaning |
|-----|---------|
| **Must** | Chặn “stage complete” / success criteria nếu giữ diagram/SPEC hiện tại |
| **Should** | Nên xử lý sớm; có thể chấp nhận tạm nếu ghi rõ trong SPEC |
| **Nice** | Sau Gold / polish |
| **Decision** | Chubby chọn options trước khi code |
| **Code** | Sửa implementation |
| **Doc** | Sửa README / SPEC / diagram |

**Labels in this file:**

- **Fact** = đã verify trên disk (2026-11-18)
- **Open decision** = chưa khóa; ghi đáp án Chubby vào ô Answer

---

## A. Điểm lệch (D01–D12)

Tick `Status`: `[ ]` open · `[x]` done (đã quyết + đã update docs/code theo quyết định).

| Status | ID | Area | SPEC / sơ đồ | Code hôm nay (Fact) | Sev | Target |
|:------:|----|------|--------------|---------------------|-----|--------|
| [x] | D01 | ID source Stage 4 | Bronze → extract IDs | **Done 18/11:** `extract_ids` + enrich đọc Bronze | **Must** | **code** (Q-A=2) |
| [x] | D02 | Parallel fan-out | SP ∥ RB từ EX | **Done 18/11:** `run_bronze` extract once → SP → RB (logical) | **Should** | **code** (Q-B=2) |
| [x] | D03 | `features_found` | Cột Silver + Gold coverage | **W4 done:** `dim_track.features_found` từ Bronze ReccoBeats | **Must** | **code** (Q-E=1→W4) |
| [x] | D04 | Silver C10 | `fact_chart` + dims + LEFT JOIN | **W1–W6 done:** `build_silver` one-pass | **Must** | **code** |
| [ ] | D05 | Gold / backfill / offline | C11–C12; `run --offline` | `gold` / `backfill` stub; `run` Bronze-only done | **Must** | Code (Silver+) |
| [ ] | D06 | C2 HTTP 429 | Shared session + Retry-After | `clients/http.py` stub; Spotify chưa 429; RB tự retry | **Should** | Nice / Code |
| [x] | D07 | Spotify batch | `?ids=` + `/{id}` | Chỉ `/{id}` — **accepted MVP** (Q-D=2) | **Should** | **Doc** (batch deferred) |
| [x] | D08 | Models C6 | Track / Artist / AudioFeatures | **Track+Artist+AudioFeatures done (W2–W4)** | **Should** | **code** |
| [ ] | D09 | Analytics C13 | summary / movers / mood | stubs | **Nice** | Code (sau Gold) |
| [x] | D10 | README status | — | Synced 18/11: Bronze + Silver C10; SoR Postgres | **Should** | **Doc** |
| [x] | D11 | SPEC storage | Postgres SoR | Synced 18/11: #4 + Tech Stack = Postgres (Q-C=1) | **Should** | **Doc** |
| [ ] | D12 | Offline E2E | `run --offline` Bronze→Silver→Gold | `--offline` stub | **Must** *(nếu giữ success)* | Code + tests |

**Không lệch (Fact — baseline giữ):** C7 watermark · C8 `music.raw_*` (+ FS dual-write optional) · C9 ingest/enrich → Bronze · ReccoBeats `?ids=` ≤40 + hits/misses · không gọi Spotify audio-features · extract-from-Bronze · `run` Bronze-only.

---

## B0. Phân loại mỗi lệch

Với từng D01–D12, chọn một rồi ghi Change log SPEC:

- [ ] Đã phân loại hết: **sửa SPEC (chấp nhận lệch)** / **sửa code** / **hoãn** *(D05–D06, D08, D09, D12 còn mở; D04=**code**)*

| ID | Phân loại (SPEC / code / hoãn) | Note |
|----|--------------------------------|------|
| D01 | **code** | Chubby: ID sau Bronze; Q-A=2 |
| D02 | **code** | Chubby: 1 extract → fan-out; Q-B=2 (logical sequential OK) |
| D03 | **code** (done W4) | Chubby: coverage/`features_found` vào Silver; Q-E=1 |
| D04 | **code** (done W1–W6) | Silver C10 MVP via `build_silver`; W7 docs |
| D05 | | |
| D06 | | Nice: shared 429 |
| D07 | **Doc** | Q-D=2: single-ID MVP; batch `?ids=` deferred (no C-3 until probe) — 18/11 |
| D08 | | |
| D09 | | |
| D10 | **Doc** | README status/stack synced 18/11 |
| D11 | **Doc** | Q-C=1: Postgres `music.*` SoR; SQLite #4 overridden for MVP — 18/11 |
| D12 | | |

---

## B1. Quyết định trước khi code *(Open decision)*

- [x] **Q-A** ID source cho enrich
  - (1) Giữ live Charts → đổi diagram/SPEC
  - (2) Extract từ `music.raw_charts` (đúng diagram)
  - (3) Hybrid: ưu tiên Bronze, fallback live
  - **Answer:** **2** (primary = Bronze). *(Chubby 18/11)*

- [x] **Q-B** Fan-out SP ∥ RB
  - (1) Sequential OK MVP
  - (2) `run` gọi song song / gần-song song
  - **Answer:** **2** — extract một lần → fan-out; MVP sequential = *logical fan-out*. *(Chubby 18/11)*

- [x] **Q-C** Silver/Gold store
  - (1) Postgres `music.*` (DDL đã có)
  - (2) SQLite như Assumption #4 gốc
  - (3) Postgres + SQLite tạm
  - **Answer:** **1** — Postgres `music.*` SoR (Bronze now + Silver/Gold target). SQLite không còn MVP SoR. *(Chubby 18/11 via C2 doc path)*

- [x] **Q-D** Spotify batch
  - (1) Implement `?ids=` + fallback `/{id}` ngay
  - (2) Single-only đến khi probe Client ID
  - (3) Probe trước rồi chọn
  - **Answer:** **2** — MVP = single `/{id}` only; không implement `?ids=` now. Batch reopen sau F5 probe nếu cần. *(Chubby 18/11)*

- [x] **Q-E** `features_found` xuất hiện khi nào
  - (1) Chỉ khi Silver
  - (2) Chấp nhận CLI hits/misses tạm cho Stage 4
  - **Answer:** **1** + **hoãn D03**. *(Chubby 18/11)*

- [x] **Q-F** “Stage 4 done” nghĩa là
  - (1) `raw_*` đủ cho watermark
  - (2) Phải extract-from-Bronze
  - (3) Phải có `features_found` ở Silver
  - **Answer:** **2**. *(Chubby 18/11)*

---

## B2. Verify live (ghi số liệu — Fact capture)

- [x] **F1** Live Charts `chart_date` = `2026-11-12` (YYYY-MM-DD)
- [ ] **F2** `COUNT(*)` `raw_charts`=___ / `raw_spotify`=___ / `raw_reccobeats`=___
- [x] **F3** Enrich watermark match — OK enrich-spotify 50 tracks / 59 artists *(18/11)*
- [x] **F4** ReccoBeats Silver apply: hits=32 misses=18 tracks=50 *(build-silver 18/11)*
- [x] **F5** Spotify `GET /v1/tracks?ids=` — **skipped / N/A for now (Q-D=2)**; probe lại trước khi mở C-3
- [ ] **F6** Deprecated fields null? popularity/genres/followers sample noted
- [x] **F7** `COUNT(*)` post-Silver W1–W4: `fact_chart≈50` / `dim_track≈50` / `dim_artist≈59` (CLI upserts 18/11; confirm SQL editor optional)
- [ ] **F8** FS dual-write dưới `data/bronze/` khớp run? yes / no

---

## B3. Doc updates (sau B1)

- [x] **DOC-1** `README.md` — status: Bronze + Silver C10 `build-silver`; Gold/`--offline` stub; SoR Postgres *(18/11)*
- [x] **DOC-2** `docs/SPEC.md` — Tech Stack / Assumption #4 + #8 + Silver C10 change log *(18/11)*
- [ ] **DOC-3** Diagram / mermaid — theo Q-A (và Q-B nếu cần)
- [ ] **DOC-4** SPEC Commands / C14 — sequential vs parallel theo Q-B
- [x] **DOC-5** Open Q1 (batch) — closed for MVP via Q-D=2; F5 skipped *(18/11)*
- [ ] **DOC-6** Success Criteria — chỉ tick khi thật đạt

---

## B4. Code slices (sau B1)

- [x] **C-1** `extract_ids` từ `music.raw_charts` → wire enrich_* *(2026-11-18)*
- [x] **C-2** C6 models Track / Artist / AudioFeatures (+ `features_found`) *(W2–W4)*
- [ ] **C-3** C4 Spotify `?ids=` + fallback — **deferred** (Q-D=2; chỉ reopen sau F5 / Q-D≠2)
- [ ] **C-4** C2 `http.py` + wire 429 Spotify/ReccoBeats *(Nice D3)*
- [x] **C-5** C10 Silver: fact + dims + LEFT JOIN + `features_found` → **W1–W6 done** (`build_silver`)
- [ ] **C-6** C11 Gold + coverage % → **§E G1–G6** (active)
- [ ] **C-7** C12 backfill `features_found=false`
- [x] **C-8** C14 `run` Bronze-only (extract once → SP → RB); `--offline` vẫn chưa
- [ ] **C-9** C13 analytics `--report` (Nice)
- [x] **C-10** Tests theo slice (LEFT JOIN / COALESCE W5; chunk 41 done; fixture offline still open)

---

## C. Suggested code slice order

```text
Done (Bronze Stage 4 + doc lock 18/11):
  C-1 extract_ids · C-8 run Bronze-only · DOC-1/2/5 · Q-C=1 · Q-D=2

Nice (trigger):
  C-4 shared 429 → ThreadPool parallel → albums enrich

Done (Silver C10 W1–W7 18/11):
  C-2 · C-5 · C-10 (LEFT JOIN) · D03 · D04 · §D W1–W7

Gold C11 slice order (active — see §E):
  G1 coverage → G2 movers → G3 mood → G4 popularity (skip-safe)
  → G5 SCD2 soft → G6 build-gold CLI → G7 docs
  (GQ-8: wire run→Gold only after G6; like SQ-11)

Later:
  C-7 backfill → C-9 analytics → D12 offline
  C-3 only if Q-D reopened after F5 probe
  SQ-11: wire run→Silver (optional follow-up)
```

Preconditions met: **D01+D02** · **Q-C=1**. Silver C10 MVP **complete** (D04 [x]). Gold checklist **§E active** (D05 open).

---

## D. Silver C10 (W1–W7)

**Links:** [D03](#a-điểm-lệch-d01d12) · [D04](#a-điểm-lệch-d01d12) · [C-5](#b4-code-slices-sau-b1) · [C-2](#b4-code-slices-sau-b1) · SPEC [C10](SPEC.md) · DDL [`docs/sql/music_schema.sql`](sql/music_schema.sql)

**Fact (locked):** Bronze Stage 4 COMPLETE. Silver reads **only** `music.raw_*` — **no HTTP**. **W1–W7 done:** fact · dims · bridge · features · LEFT JOIN tests · `build_silver` one-pass · docs. Soft SQ-11: `run` still Bronze-only.

### 1. Preconditions

- [x] D01 + D02 done (extract-from-Bronze + logical fan-out)
- [x] Q-C=1 Postgres `music.*` SoR
- [x] `music.raw_charts` / `raw_spotify` / `raw_reccobeats` populated for at least one watermark
- [x] DDL Silver tables exist (`fact_chart`, `dim_track`, `dim_artist`, `bridge_track_artist`)
- [x] B0 D04 classified **code** (Silver checklist start)
- [x] F7 post-Silver captured (≈50/50/59 via CLI upserts 18/11)

### 2. Soft decisions (Recommendations — not Facts)

| ID | Decision | Notes |
|----|----------|-------|
| **SQ-1** | Watermark CLI like ingest/enrich | `chart_date` / `chart_type` / `country` args on Silver commands |
| **SQ-2** | `raw_charts` = latest `ingested_at` | Same grain as `extract_ids` happy path |
| **SQ-3** | `raw_spotify` = latest per `spotify_id` + `entity` | Avoid stale dual-writes |
| **SQ-5** | W1 fact-only first; one-pass CLI later | Defer unified CLI to **W6** |
| **SQ-6** | `streams=NULL` (`public/v0`) | Matches SPEC MVP; no auth/v0 |
| **SQ-7** | `artist_position` 0-based from `track.artists` | Bridge order = Spotify array index |
| **SQ-11** | Wire `run` → Silver **after W6** | Keep `run` Bronze-only until one-pass CLI exists |

### 3. Work packages (tickable)

#### W1 — `fact_chart` only (PR #1 / S)

- **Status:** [x] *(2026-11-18: `build_fact_chart` + CLI `build-silver` fact-only)*
- **In:** Parse latest `raw_charts` for watermark → upsert `music.fact_chart`
- **Out:** dims, bridge, features, CLI one-pass, HTTP, Gold
- **Steps:**
  1. Read latest Bronze charts payload for watermark (SQ-2)
  2. Map rank / prev_rank / track_id / entry_status; `streams=NULL` (SQ-6)
  3. Upsert PK `(chart_date, chart_type, country, track_id)`
  4. Minimal CLI or script path to run W1 for one watermark (SQ-1); full one-pass deferred to W6 (SQ-5)
- **Files:** `src/spotify_pipeline/pipeline/silver.py` · reuse `extract_ids` / chart model patterns · `cli.py` (thin stub OK) · tests for fact upsert
- **AC:**
  - Given Bronze `raw_charts` for watermark W, when Silver fact builder runs, then `fact_chart` row count matches chart entries and PK upsert is idempotent
  - `streams` is NULL for `public/v0`
  - No HTTP calls; no writes to `dim_*` / bridge
- **Depends:** Preconditions · Soft SQ-1, SQ-2, SQ-5, SQ-6
- **Closes / advances:** D04 (partial) · C-5 (start)

#### W2 — `dim_track` from `raw_spotify` track

- **Status:** [x] *(2026-11-18: `build_dim_track` + TrackMetadata; CLI after fact)*
- **In:** Latest track payloads → upsert `music.dim_track` metadata (no ReccoBeats yet)
- **Out:** artist dim/bridge, features_found logic, fact rebuild
- **Steps:**
  1. Read latest `raw_spotify` where `entity=track` per `spotify_id` (SQ-3)
  2. Map SPEC dim_track metadata cols; `features_found` stays default `false` until W4
  3. Upsert on `track_id`; do not invent feature values
  4. Implement/extend C6 Track model stub as needed for validation (ties C-2)
- **Files:** `pipeline/silver.py` · `models/track.py` · tests
- **AC:**
  - Given track Bronze rows, when W2 runs, then `dim_track` has metadata for those IDs
  - Deprecated / missing popularity fields remain nullable
  - Re-run does not duplicate PKs
- **Depends:** W1 (recommended sequencing; fact can exist without dims) · SQ-3 · C-2 as needed
- **Closes / advances:** D08 (partial Track) · C-2 · C-5

#### W3 — `dim_artist` + `bridge_track_artist`

- **Status:** [x] *(2026-11-18: `build_dim_artist_bridge` + ArtistMetadata)*
- **In:** Artist payloads + track.artists → `dim_artist` + bridge
- **Out:** ReccoBeats features, COALESCE merge, one-pass CLI
- **Steps:**
  1. Latest `raw_spotify` `entity=artist` per id (SQ-3)
  2. Upsert `dim_artist` (nullable genres/followers/popularity)
  3. Build `bridge_track_artist` with `artist_position` 0-based from `track.artists` (SQ-7)
  4. Respect FK: track must exist in `dim_track` (W2) before bridge insert
- **Files:** `pipeline/silver.py` · `models/track.py` (artists) · tests for bridge order
- **AC:**
  - Bridge PK `(track_id, artist_id)` idempotent; positions match Spotify artist array order (0-based)
  - Multi-artist tracks produce multiple bridge rows
  - Missing optional artist fields do not fail the build
- **Depends:** W2 · SQ-3 · SQ-7
- **Closes / advances:** D08 (Artist) · C-5

#### W4 — ReccoBeats → `features_found` (closes D03)

- **Status:** [x] *(2026-11-18: `build_dim_track_features`; D03 closed)*
- **In:** Latest `raw_reccobeats` → fill audio feature cols + `features_found` / `features_fetched_at` / `source_features='reccobeats'`
- **Out:** Gold, backfill job, HTTP re-fetch
- **Steps:**
  1. Read Bronze ReccoBeats payloads for watermark track set (no HTTP)
  2. Matched IDs → features + `features_found=true`
  3. Chart tracks missing from ReccoBeats content → keep row, `features_found=false` (SPEC BR-5)
  4. Implement/extend `models/audio_features.py` (+ `features_found`) as needed (C-2)
- **Files:** `pipeline/silver.py` · `models/audio_features.py` · tests (miss keeps chart; hit sets flag)
- **AC:**
  - Hits set features + `features_found=true` + `source_features='reccobeats'`
  - Misses leave/keep `features_found=false` without deleting `fact_chart` rows
  - **D03** can be ticked done after this lands + docs note
- **Depends:** W2 (dim_track row to update) · Q-E=1
- **Closes:** **D03** · advances C-2 / C-5

#### W5 — LEFT JOIN + COALESCE

- **Status:** [x] *(2026-11-18: `sql_fact_chart_left_join_dim_track` + COALESCE tests)*
- **In:** Enforce SPEC join/upsert semantics across fact↔dims and dim_track metadata↔features
- **Out:** New tables, Gold views logic changes, backfill
- **Steps:**
  1. Any chart↔track/feature read path uses **LEFT JOIN** — never drop chart rows (SPEC BR-6)
  2. `dim_track` `ON CONFLICT` uses **COALESCE** so metadata-only upsert does not wipe features and feature upsert does not wipe metadata (per SPEC DDL notes)
  3. Regression test: fact rows survive missing dim/features; COALESCE round-trip
- **Files:** `pipeline/silver.py` · SQL upsert helpers · tests (LEFT JOIN + COALESCE)
- **AC:**
  - Missing features/genres/popularity never removes `fact_chart` rows
  - Metadata-then-features and features-then-metadata both preserve non-null sides via COALESCE
- **Depends:** W1–W4
- **Closes / advances:** C-5 (join fidelity) · C-10 tests slice

#### W6 — `build-silver` one-pass CLI

- **Status:** [x] *(2026-11-18: `build_silver()` + CLI; live OK watermark 2026-11-12)*
- **In:** Single CLI command runs fact + dims + bridge + features for one watermark
- **Out:** Wiring into `run` (SQ-11 later), Gold, offline E2E full
- **Steps:**
  1. Implement `cli.py` `build-silver` with watermark args (SQ-1)
  2. Orchestrate W1→W4 builders in one pass inside `pipeline/silver.py` (`build_silver`)
  3. Exit codes / summary counts consistent with ingest/enrich style
  4. Do **not** auto-wire `run` → Silver yet (SQ-11)
- **Files:** `cli.py` · `pipeline/silver.py` · tests for one-pass
- **AC:**
  - `python -m spotify_pipeline build-silver --chart-date 2026-11-12 --chart-type weekly_top_songs --country global` completes from Bronze-only inputs
  - Idempotent re-run for same watermark
  - `run` remains Bronze-only until explicit SQ-11 follow-up
- **Depends:** W1–W5 · SQ-1 · SQ-5 · SQ-11
- **Closes:** **D04** / **C-5** (Silver MVP builder)

#### W7 — checklist / docs hygiene

- **Status:** [x] *(2026-11-18: README/SPEC/checklist synced)*
- **In:** Tick gaps, sync README/SPEC status, B0 notes, F7 capture
- **Out:** Gold implementation, new product features
- **Steps:**
  1. Mark D03/D04/C-5/C-2 progress accurately after W4/W6
  2. Update README status: C10 builder live (scope of what landed)
  3. SPEC change-log line for Silver C10 MVP + soft SQ-* if promoted to Fact
  4. Capture F7 counts post-Silver
- **Files:** `docs/CHECKLIST_SPEC_GAPS.md` · `README.md` · `docs/SPEC.md` (change log / status only)
- **AC:**
  - Checklist Status ticks match code reality
  - No invented BRs; soft SQ-* either still labeled soft or promoted with Chubby Answer
- **Depends:** W6 (or incremental after each W* if preferred)
- **Closes:** Doc hygiene for Silver slice

### 4. Out of scope (this Silver checklist)

- Gold (C11 / C-6)
- Backfill job (C12 / C-7)
- `run --offline` full Bronze→Silver→Gold (D12)
- Analytics / `--report` (C13)
- Spotify batch `?ids=` (C-3 / D07 deferred)
- Shared HTTP 429 session (C-4 / D06)
- Wire `run` → Silver on day 1 (**SQ-11** = after W6 only)
- Charts `auth/v0` streams
- Albums enrich / ThreadPool parallel Nice path

### 5. Suggested order + first PR

```text
W1 → W2 → W3 → W4 → W5 → W6 → W7
```

**First PR title:** `feat(silver): W1 upsert fact_chart from raw_charts`

Optional PR sizing: W1 alone (S) · W2+W3 · W4+W5 · W6 · W7 docs.

### 6. B0 note (D04)

When Silver coding starts (W1 kickoff): set B0 **D04 = code** (done in this pass). Keep **D03 = hoãn** until **W4** lands, then reclassify D03 to **code** (done) / tick Status in §A.

---

## E. Gold C11 (G1–G7)

**Links:** [D05](#a-điểm-lệch-d01d12) · [C-6](#b4-code-slices-sau-b1) · [C-9](#b4-code-slices-sau-b1) *(Nice analytics)* · SPEC [C11](SPEC.md) · [Gold analytics MVP](SPEC.md#gold-analytics-mvp) · DDL [`docs/sql/music_schema.sql`](sql/music_schema.sql) · Silver [§D](#d-silver-c10-w1w7) (W1–W7 done)

**Fact (locked):** Silver C10 MVP **COMPLETE** (W1–W7). Gold must read **only** Silver (`music.fact_chart` / `dim_*` / bridge as needed) — **no HTTP**, no Bronze re-parse required for MVP. DDL already has VIEWs: `gold_feature_coverage`, `gold_movers`, `gold_mood_segments`. Stubs: `pipeline/gold.py`, `cli.py build-gold`, `analytics/{movers,mood,summary}.py`.

**Diagram ↔ DDL mismatches (Fact — do not silently “fix” without soft decision):**

- Diagram shows **SCD2 rank history** table; DDL has **no** SCD2 object (SPEC: formal SCD2 = nice-to-have).
- Diagram Silver path is LEFT JOIN; `gold_mood_segments` uses **INNER JOIN** + `features_found=true` — intentional mood filter, **not** a BR-6 chart-row drop (coverage VIEW remains LEFT JOIN).
- Diagram movers include **new / re-entry**; current `gold_movers` filters `prev_rank IS NOT NULL` and only exposes `rank_delta` (SPEC MVP text = delta only).
- Diagram genre analysis; SPEC Gold MVP does **not** require genre (genres deprecated / often null).
- BI tool undecided (SPEC Assumption #7).

### 1. Preconditions

- [x] Silver C10 W1–W7 done (`build_silver`; fact + dims + bridge + `features_found` + LEFT JOIN tests)
- [x] Q-C=1 Postgres `music.*` SoR
- [x] Gold VIEWs exist in DDL / applied schema (`gold_feature_coverage`, `gold_movers`, `gold_mood_segments`)
- [x] At least one watermark populated in Silver (F7 ≈50/50/59; F4 hits/misses noted)
- [ ] B0 **D05** classified (**code** recommended when G1 starts)
- [ ] Soft **GQ-*** answered or explicitly “proceed with Recommendation”

### 2. Soft decisions (Recommendations — not Facts)

| ID | Decision | Recommendation | Notes |
|----|----------|----------------|-------|
| **GQ-1** | Gold store shape | Keep existing **plain VIEWs**; query in Python | MATERIALIZED + REFRESH = Nice later |
| **GQ-2** | Movers new / re-entry | **MVP = VIEW as-is** (`rank_delta` where `prev_rank IS NOT NULL`) | New/re-entry = Nice after Chubby Answer; don’t invent statuses |
| **GQ-3** | Mood thresholds | Document energy×valence cutovers in **code comments** (SPEC) | e.g. 0.5/0.5 quadrants — Assumption until Chubby locks numbers |
| **GQ-4** | Popularity vs features | **Null-safe skip** on current Dev Mode (Open Q2: popularity absent) | Optional stub query OK; no DDL required; never fail build |
| **GQ-5** | SCD2 | **Defer formal table**; MVP = append-only `fact_chart` query if needed | Matches SPEC nice-to-have; diagram-only until promoted |
| **GQ-6** | C13 analytics modules | Thin helpers inside `pipeline/gold.py` for CLI summary; leave `analytics/*` stubs until **C-9** | Avoid dual logic |
| **GQ-7** | Watermark CLI args | Same as Silver: `chart_date` / `chart_type` / `country` | Mirror `build-silver` |
| **GQ-8** | Wire `run` → Gold | **Do not** in this checklist | Same spirit as SQ-11; after G6 + optional offline |
| **GQ-9** | Streams in movers output | Include column; treat as display-only when NULL | `public/v0` = all NULL |
| **GQ-10** | Genre Gold path | **Out of MVP** unless Chubby reopens | Deprecated / empty on current app |

### 3. Work packages (tickable)

#### G1 — Feature coverage (validate `gold_feature_coverage`)

- **Status:** [ ]
- **In:** Query existing `music.gold_feature_coverage` for watermark; optional missing top-N list via Silver LEFT JOIN (`features_found is not true`)
- **Out:** Movers/mood math, SCD2, HTTP, Bronze reads, MATERIALIZED refresh unless GQ-1 changes
- **Steps:**
  1. Confirm VIEW definition matches SPEC (% found, grain = chart_date×chart_type×country)
  2. Add thin reader in `pipeline/gold.py` filtered by watermark (GQ-7)
  3. Optional: list missing top-N ranks (SPEC coverage report) without dropping chart grain
  4. Unit test against fixture/SQL expectations (no network)
- **Files:** `src/spotify_pipeline/pipeline/gold.py` · tests · reuse Silver LEFT JOIN helper if useful
- **AC:**
  - Given Silver for watermark W, when coverage runs, then `chart_rows` / `features_found_rows` / `features_found_pct` match VIEW
  - Coverage path uses LEFT JOIN semantics for chart completeness (BR-6 spirit)
  - No HTTP
- **Depends:** Preconditions · GQ-1 · GQ-7
- **Closes / advances:** D05 (partial) · **C-6** (start)

#### G2 — Movers (`gold_movers` + streams null-safe)

- **Status:** [ ]
- **In:** Read `music.gold_movers` for watermark; expose `rank_delta` (= `prev_rank - rank`, positive = up)
- **Out:** Formal new/re-entry taxonomy (unless GQ-2 promoted), SCD2, genre, HTTP
- **Steps:**
  1. Query VIEW; filter watermark
  2. Document VIEW filter: rows with `prev_rank IS NULL` excluded (GQ-2)
  3. Streams: pass through; summary/report include streams **only when NOT NULL** (GQ-9)
  4. Test delta sign + null streams on `public/v0`
- **Files:** `pipeline/gold.py` · optional thin `analytics/movers.py` only if GQ-6 says so · tests
- **AC:**
  - Rank delta matches SPEC formula
  - `streams` null does not fail movers
  - No chart rows deleted in Silver as side effect
- **Depends:** G1 (recommended) · GQ-2 · GQ-9
- **Closes / advances:** C-6

#### G3 — Mood segments (`features_found=true`)

- **Status:** [ ]
- **In:** Read `music.gold_mood_segments`; assign mood labels from energy×valence (GQ-3)
- **Out:** Genre analysis, changing VIEW to LEFT JOIN (would contradict SPEC mood filter), HTTP
- **Steps:**
  1. Query VIEW (INNER JOIN + `features_found IS TRUE` — Fact in DDL)
  2. Add quadrant/segment labels in code; **document thresholds in comments** (SPEC)
  3. Note in code/docs: filter ≠ BR-6 violation; coverage still reports misses
  4. Test: miss tracks absent from mood; hit tracks labeled; `source_features` preserved
- **Files:** `pipeline/gold.py` · optional `analytics/mood.py` (GQ-6) · tests
- **AC:**
  - Mood output only where `features_found=true`
  - Empty mood allowed when coverage < 100%; build still succeeds
  - Thresholds documented in comments
- **Depends:** G1 · GQ-3 · GQ-6
- **Closes / advances:** C-6 (mood)

#### G4 — Popularity vs features (null-safe optional)

- **Status:** [ ]
- **In:** Optional scatter/pairs query: `track_popularity` vs selected audio features where both present
- **Out:** Failing the build when popularity absent; new mandatory DDL; claiming feasibility on current Dev Mode without caveat
- **Steps:**
  1. Implement null-safe path (GQ-4): if no non-null `track_popularity` for watermark → skip + message
  2. Do **not** require new VIEW for MVP (Assumption: ad-hoc SQL OK)
  3. Test: all-null popularity → skip; mixed → only non-null pairs
- **Files:** `pipeline/gold.py` · tests
- **AC:**
  - Gold completes when popularity absent (BR-10 / Open Q2)
  - No invented popularity values
- **Depends:** G3 recommended · GQ-4
- **Closes / advances:** C-6 (optional slice)

#### G5 — SCD2 rank history (soft)

- **Status:** [ ]
- **In:** Per GQ-5 — either (A) defer formal SCD2 with checklist note, or (B) thin history query over append-only `fact_chart` (`valid_from`/`valid_to` **not** persisted)
- **Out:** New SCD2 table/DDL without Chubby Answer; rewriting Silver grain
- **Steps:**
  1. Lock GQ-5 Answer (Recommend: **defer formal**)
  2. If defer: document diagram mismatch in G7; no code beyond comment/README
  3. If thin query: read-only SQL by `(track_id, chart_type, country)` ordered by `chart_date`; no `is_current` table
  4. Test only if (B) implemented
- **Files:** docs and/or `pipeline/gold.py` query helper · **no** DDL unless Answer promotes formal
- **AC:**
  - Formal SCD2 table remains absent unless explicitly promoted
  - MVP history (if any) is query-only on `fact_chart`
- **Depends:** GQ-5 · G2 useful for multi-date context
- **Closes / advances:** Nice / diagram honesty (not Must for Gold MVP per SPEC)

#### G6 — `build-gold` one-pass CLI + summary

- **Status:** [ ]
- **In:** Single CLI command runs G1–G3 (+ G4 skip path; G5 per soft) for one watermark; prints coverage / movers / mood counts
- **Out:** Wire into `run` (GQ-8 later), full `--offline` E2E (D12), backfill C12, rich C13 `--report` (C-9)
- **Steps:**
  1. Replace `cli.py` `build-gold` stub with watermark args (GQ-7)
  2. Orchestrate `build_gold()` in `pipeline/gold.py`
  3. Exit codes / summary style consistent with `build-silver`
  4. Do **not** auto-wire `run` → Gold (GQ-8)
- **Files:** `cli.py` · `pipeline/gold.py` · tests for one-pass
- **AC:**
  - `python -m spotify_pipeline build-gold --chart-date … --chart-type … --country …` completes from Silver-only inputs
  - Summary includes coverage % (Success / Objective)
  - Idempotent re-query; `run` unchanged
- **Depends:** G1–G3 · GQ-7 · GQ-8
- **Closes:** **C-6** Gold MVP builder (D05 advanced; full D05 also needs backfill/offline — still open)

#### G7 — checklist / docs hygiene

- **Status:** [ ]
- **In:** Tick gaps; sync README/SPEC status; record GQ-* Answers; note diagram↔DDL mismatches
- **Out:** New product features, BI tool choice, invented BRs
- **Steps:**
  1. Mark D05/C-6 progress accurately after G6
  2. README: Gold builder live (scope of what landed); BI still TBD
  3. SPEC change-log line for Gold C11 MVP + soft GQ promotions
  4. Link this §E from §C order; keep C-9 / C-7 / D12 out of “done” unless true
- **Files:** `docs/CHECKLIST_SPEC_GAPS.md` · `README.md` · `docs/SPEC.md` (change log / status only)
- **AC:**
  - Checklist Status ticks match code reality
  - No invented BRs; GQ-* labeled soft or promoted with Chubby Answer
  - Explicit notes: mood INNER JOIN; SCD2 not in DDL; popularity optional/skip
- **Depends:** G6 (or incremental after each G*)
- **Closes:** Doc hygiene for Gold slice

### 4. Out of scope (this Gold checklist)

- Backfill job (C12 / C-7)
- `run --offline` full Bronze→Silver→Gold (D12)
- Analytics `--report` polish (C13 / C-9) beyond thin CLI summary
- Wire `run` → Silver/Gold (**GQ-8** / SQ-11)
- Formal SCD2 table DDL (unless GQ-5 promoted)
- Genre Gold analysis (GQ-10)
- Charts `auth/v0` streams enablement
- BI dashboard product
- Spotify batch `?ids=` / shared HTTP 429
- Calling any external HTTP from Gold

### 5. Suggested order + first PR

```text
G1 → G2 → G3 → G4 → G5 → G6 → G7
```

**First PR title:** `feat(gold): G1 query gold_feature_coverage for watermark`

Optional PR sizing: G1 alone (S) · G2+G3 · G4+G5 (soft/docs-heavy) · G6 · G7 docs.

### 6. Links to D05 / C-6 / C-9

| ID | Role in Gold |
|----|----------------|
| **D05** | Parent gap: Gold / backfill / offline — this §E closes **Gold builder slice** only; backfill+offline remain |
| **C-6** | Code slice: C11 Gold + coverage % — primary close target of G1–G6 |
| **C-9** | Nice: C13 analytics `--report` — **after** G6; do not block Gold MVP |

**B0 note (D05):** When Gold coding starts (G1 kickoff): set B0 **D05 = code** (partial until C-7/D12). Tick §A D05 only when Chubby defines “done” for the whole D05 row (Gold+backfill+offline) or split the row in a later pass.

---

## Facts vs open decisions (tóm tắt)

| Type | Statement |
|------|-----------|
| **Fact** | C7–C9 Bronze landing (ingest + enrich → `raw_*`); SoR Postgres; FS dual-write optional |
| **Fact** | Enrich ID source = **Bronze `raw_charts`** via `extract_ids` (C-1 done) |
| **Fact** | `run` Bronze-only; **Silver C10 W1–W7 complete** (`build_silver`); Gold checklist §E drafted; `gold.py` / backfill / offline still stub |
| **Fact** | Gold DDL VIEWs present (`gold_feature_coverage` / `gold_movers` / `gold_mood_segments`); Gold **reads only** Silver (no HTTP) |
| **Chốt 18/11** | Q-A=2 · Q-B=2 · **Q-C=1** · **Q-D=2** · Q-E=1 (**D03/D04 closed**) · Q-F=2 |
| **Doc done 18/11–19/11** | D03 · D04 · D07 · D08 · D10 · D11 · DOC-1 · DOC-2 · DOC-5 · F1/F3/F4/F7 · W1–W7 · **§E Gold G1–G7** |
| **Soft (SQ-* / GQ-*)** | SQ-11 still soft; **GQ-1…GQ-10** Recommendations for Gold (see §E) |
| **Open** | D05 · D06 · D09 · D12 · Nice D3→D1→D2 · Gold G1–G7 · SQ-11 · GQ-* Answers |
