# Checklist: SPEC / diagram ↔ code gaps

**Purpose:** Working checklist để tick lệch, ghi quyết định Chubby, rồi update docs/code — không invent BR mới.  
**Source of truth:** [`docs/SPEC.md`](SPEC.md)  
**Last updated:** 2026-11-18  

### Files updated this pass (Q-D=2 + C1/C2 doc lock)

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
| [ ] | D03 | `features_found` | Cột Silver + Gold coverage | Chỉ CLI `hits`/`misses` (enrich-reccobeats) | **Must** | **hoãn** (Q-E=1) |
| [ ] | D04 | Silver C10 | `fact_chart` + dims + LEFT JOIN | `pipeline/silver.py` stub | **Must** | Code |
| [ ] | D05 | Gold / backfill / offline | C11–C12; `run --offline` | `gold` / `backfill` stub; `run` Bronze-only done | **Must** | Code (Silver+) |
| [ ] | D06 | C2 HTTP 429 | Shared session + Retry-After | `clients/http.py` stub; Spotify chưa 429; RB tự retry | **Should** | Nice / Code |
| [x] | D07 | Spotify batch | `?ids=` + `/{id}` | Chỉ `/{id}` — **accepted MVP** (Q-D=2) | **Should** | **Doc** (batch deferred) |
| [ ] | D08 | Models C6 | Track / Artist / AudioFeatures | `track.py` / `audio_features.py` stub | **Should** | Code (cùng Silver) |
| [ ] | D09 | Analytics C13 | summary / movers / mood | stubs | **Nice** | Code (sau Gold) |
| [x] | D10 | README status | — | Synced 18/11: Bronze/`run` live; SoR Postgres | **Should** | **Doc** |
| [x] | D11 | SPEC storage | Postgres SoR | Synced 18/11: #4 + Tech Stack = Postgres (Q-C=1) | **Should** | **Doc** |
| [ ] | D12 | Offline E2E | `run --offline` Bronze→Silver→Gold | `--offline` stub | **Must** *(nếu giữ success)* | Code + tests |

**Không lệch (Fact — baseline giữ):** C7 watermark · C8 `music.raw_*` (+ FS dual-write optional) · C9 ingest/enrich → Bronze · ReccoBeats `?ids=` ≤40 + hits/misses · không gọi Spotify audio-features · extract-from-Bronze · `run` Bronze-only.

---

## B0. Phân loại mỗi lệch

Với từng D01–D12, chọn một rồi ghi Change log SPEC:

- [ ] Đã phân loại hết: **sửa SPEC (chấp nhận lệch)** / **sửa code** / **hoãn** *(D04–D06, D08, D09, D12 còn mở)*

| ID | Phân loại (SPEC / code / hoãn) | Note |
|----|--------------------------------|------|
| D01 | **code** | Chubby: ID sau Bronze; Q-A=2 |
| D02 | **code** | Chubby: 1 extract → fan-out; Q-B=2 (logical sequential OK) |
| D03 | **hoãn** | Chubby: coverage/`features_found` vào Silver; Q-E=1 |
| D04 | | *(chưa khóa — sau Bronze fidelity)* |
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

- [ ] **F1** Live Charts `chart_date` = `__________` (YYYY-MM-DD)
- [ ] **F2** `COUNT(*)` `raw_charts`=___ / `raw_spotify`=___ / `raw_reccobeats`=___
- [ ] **F3** Enrich watermark match / fail message captured
- [ ] **F4** ReccoBeats 1 watermark: hits=___ misses=___ tracks=___
- [x] **F5** Spotify `GET /v1/tracks?ids=` — **skipped / N/A for now (Q-D=2)**; probe lại trước khi mở C-3
- [ ] **F6** Deprecated fields null? popularity/genres/followers sample noted
- [ ] **F7** `COUNT(*)` `fact_chart` / `dim_track` / `dim_artist` (kỳ vọng 0 nếu chưa Silver)
- [ ] **F8** FS dual-write dưới `data/bronze/` khớp run? yes / no

---

## B3. Doc updates (sau B1)

- [x] **DOC-1** `README.md` — status thật: C7–C9 + `run` Bronze; C10–C14 stub; SoR Postgres *(18/11)*
- [x] **DOC-2** `docs/SPEC.md` — Tech Stack / Assumption #4 + #8 synced *(18/11)*
- [ ] **DOC-3** Diagram / mermaid — theo Q-A (và Q-B nếu cần)
- [ ] **DOC-4** SPEC Commands / C14 — sequential vs parallel theo Q-B
- [x] **DOC-5** Open Q1 (batch) — closed for MVP via Q-D=2; F5 skipped *(18/11)*
- [ ] **DOC-6** Success Criteria — chỉ tick khi thật đạt

---

## B4. Code slices (sau B1)

- [x] **C-1** `extract_ids` từ `music.raw_charts` → wire enrich_* *(2026-11-18)*
- [ ] **C-2** C6 models Track / AudioFeatures (+ `features_found`)
- [ ] **C-3** C4 Spotify `?ids=` + fallback — **deferred** (Q-D=2; chỉ reopen sau F5 / Q-D≠2)
- [ ] **C-4** C2 `http.py` + wire 429 Spotify/ReccoBeats *(Nice D3)*
- [ ] **C-5** C10 Silver: fact + dims + LEFT JOIN + `features_found` *(hoãn)*
- [ ] **C-6** C11 Gold + coverage %
- [ ] **C-7** C12 backfill `features_found=false`
- [x] **C-8** C14 `run` Bronze-only (extract once → SP → RB); `--offline` vẫn chưa
- [ ] **C-9** C13 analytics `--report` (Nice)
- [ ] **C-10** Tests theo slice (LEFT JOIN, chunk 41, fixture offline)

---

## C. Suggested code slice order

```text
Done (Bronze Stage 4 + doc lock 18/11):
  C-1 extract_ids · C-8 run Bronze-only · DOC-1/2/5 · Q-C=1 · Q-D=2

Nice (trigger):
  C-4 shared 429 → ThreadPool parallel → albums enrich

Later (Silver+):
  C-2 → C-5 Silver + features_found → C-6 Gold → C-7 backfill → …
  C-3 only if Q-D reopened after F5 probe
```

Không bắt đầu Stage 5 Silver cho đến khi **D01+D02 xong** và **Q-C** có Answer *(Q-C đã = 1; Silver builders vẫn hoãn)*.

---

## Facts vs open decisions (tóm tắt)

| Type | Statement |
|------|-----------|
| **Fact** | C7–C9 Bronze landing (ingest + enrich → `raw_*`); SoR Postgres; FS dual-write optional |
| **Fact** | Enrich ID source = **Bronze `raw_charts`** via `extract_ids` (C-1 done) |
| **Fact** | `run` Bronze-only done; Silver / Gold / backfill / analytics / `http.py` / Track+AF models = stub |
| **Chốt 18/11** | Q-A=2 · Q-B=2 · **Q-C=1** · **Q-D=2** · Q-E=1 (hoãn D03) · Q-F=2 |
| **Doc done 18/11** | D07 · D10 · D11 · DOC-1 · DOC-2 · DOC-5 · F5 skipped |
| **Open** | D03–D06 · D08 · D09 · D12 · Nice D3→D1→D2 · Silver+ |
