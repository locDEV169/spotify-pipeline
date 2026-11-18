# Checklist: SPEC / diagram ↔ code gaps

**Purpose:** Working checklist để tick lệch, ghi quyết định Chubby, rồi update docs/code — không invent BR mới.  
**Source of truth:** [`docs/SPEC.md`](SPEC.md)  
**Last updated:** 2026-11-18  

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
| [ ] | D05 | Gold / backfill / run | C11–C14 | `gold` / `backfill` / `run` + CLI stubs | **Must** | Code |
| [ ] | D06 | C2 HTTP 429 | Shared session + Retry-After | `clients/http.py` stub; Spotify chưa 429; RB tự retry | **Should** | Code |
| [ ] | D07 | Spotify batch | `?ids=` + `/{id}` | Chỉ `get_track` / `get_artist` `/{id}` | **Should** | Decision → Code *hoặc* Doc |
| [ ] | D08 | Models C6 | Track / Artist / AudioFeatures | `track.py` / `audio_features.py` stub | **Should** | Code (cùng Silver) |
| [ ] | D09 | Analytics C13 | summary / movers / mood | stubs | **Nice** | Code (sau Gold) |
| [ ] | D10 | README status | — | Header vẫn “scaffold / stubs / not implemented” dù C9 có lệnh | **Should** | Doc |
| [ ] | D11 | SPEC storage | Assumption #4 override: Postgres SoR | Tech Stack / đoạn cũ còn SQLite / mơ hồ | **Should** | Doc |
| [ ] | D12 | Offline E2E | `run --offline` Bronze→Silver→Gold | `run --offline` stub | **Must** *(nếu giữ success)* | Code + tests |

**Không lệch (Fact — baseline giữ):** C7 watermark · C8 `music.raw_*` (+ FS dual-write optional) · C9 ingest/enrich → Bronze · ReccoBeats `?ids=` ≤40 + hits/misses · không gọi Spotify audio-features.

---

## B0. Phân loại mỗi lệch

Với từng D01–D12, chọn một rồi ghi Change log SPEC:

- [ ] Đã phân loại hết: **sửa SPEC (chấp nhận lệch)** / **sửa code** / **hoãn**

| ID | Phân loại (SPEC / code / hoãn) | Note |
|----|--------------------------------|------|
| D01 | **code** | Chubby: ID sau Bronze; Q-A=2 (3=optional fallback) |
| D02 | **code** *(hoặc Doc nếu giữ 2 CLI)* | Chubby: 1 extract → fan-out; Q-B=2 (MVP sequential OK nếu ghi logical fan-out) |
| D03 | **hoãn** | Chubby: coverage/`features_found` vào Silver sau; Q-E=1 |
| D04 | | *(chưa khóa — sau Bronze fidelity)* |
| D05 | | |
| D06 | | |
| D07 | | |
| D08 | | |
| D09 | | |
| D10 | | |
| D11 | | |
| D12 | | |

---

## B1. Quyết định trước khi code *(Open decision)*

Gợi ý: khóa **Q-A** + **Q-C** trước — đổi contract lớn nhất.

- [x] **Q-A** ID source cho enrich
  - (1) Giữ live Charts → đổi diagram/SPEC
  - (2) Extract từ `music.raw_charts` (đúng diagram)
  - (3) Hybrid: ưu tiên Bronze, fallback live
  - **Answer:** **2** (primary = Bronze). **Recommendation:** optional **3** = fallback live chỉ khi thiếu `raw_charts` / empty entries — ghi rõ trong SPEC, không làm nguồn chính. *(Chubby 18/11: muốn “sau Bronze”, không re-fetch Charts live làm nguồn chính.)*

- [x] **Q-B** Fan-out SP ∥ RB
  - (1) Sequential OK MVP
  - (2) `run` gọi song song / gần-song song
  - **Answer:** **2** — một bước extract → `run` fan-out SP ∥ RB. **MVP nhỏ nhất:** sequential trong `run` vẫn OK nếu SPEC/diagram ghi *logical fan-out* (cùng ID set, không phụ thuộc lẫn nhau); ThreadPool sau nếu cần. *(Chubby 18/11: muốn đúng diagram; hiện 2 CLI tuần tự, `run` stub.)*

- [ ] **Q-C** Silver/Gold store
  - (1) Postgres `music.*` (DDL đã có)
  - (2) SQLite như Assumption #4 gốc
  - (3) Postgres + SQLite tạm
  - **Answer:** _______________

- [ ] **Q-D** Spotify batch
  - (1) Implement `?ids=` + fallback `/{id}` ngay
  - (2) Single-only đến khi probe Client ID
  - (3) Probe trước rồi chọn
  - **Answer:** _______________

- [x] **Q-E** `features_found` xuất hiện khi nào
  - (1) Chỉ khi Silver
  - (2) Chấp nhận CLI hits/misses tạm cho Stage 4
  - **Answer:** **1** + **hoãn D03** — CLI `hits`/`misses` giữ tạm Stage 4; cột `features_found` + coverage % vào Silver (C10), không chặn Bronze fidelity. *(Chubby 18/11: coverage vào Silver làm sau.)*

- [x] **Q-F** “Stage 4 done” nghĩa là
  - (1) `raw_*` đủ cho watermark
  - (2) Phải extract-from-Bronze
  - (3) Phải có `features_found` ở Silver
  - **Answer:** **2** (và ingest+enrich → `raw_*` ổn định). **Không** đòi (3) trước khi Bronze fidelity D01+D02 xong. (1) alone = chưa đủ nếu vẫn live-Charts làm ID source.

---

## B2. Verify live (ghi số liệu — Fact capture)

- [ ] **F1** Live Charts `chart_date` = `__________` (YYYY-MM-DD)
- [ ] **F2** `COUNT(*)` `raw_charts`=___ / `raw_spotify`=___ / `raw_reccobeats`=___
- [ ] **F3** Enrich watermark match / fail message captured
- [ ] **F4** ReccoBeats 1 watermark: hits=___ misses=___ tracks=___
- [ ] **F5** Spotify `GET /v1/tracks?ids=` sống trên Client ID? yes / no / not probed
- [ ] **F6** Deprecated fields null? popularity/genres/followers sample noted
- [ ] **F7** `COUNT(*)` `fact_chart` / `dim_track` / `dim_artist` (kỳ vọng 0 nếu chưa Silver)
- [ ] **F8** FS dual-write dưới `data/bronze/` khớp run? yes / no

---

## B3. Doc updates (sau B1)

- [ ] **DOC-1** `README.md` — status thật: C7–C9 done; C10–C14 stub; SoR Postgres
- [ ] **DOC-2** `docs/SPEC.md` — đồng bộ Tech Stack / Assumption #4 (18/11 override)
- [ ] **DOC-3** Diagram / mermaid — theo Q-A (và Q-B nếu cần)
- [ ] **DOC-4** SPEC Commands / C14 — sequential vs parallel theo Q-B
- [ ] **DOC-5** Open Q1 (batch) — kết quả F5 / Q-D
- [ ] **DOC-6** Success Criteria — chỉ tick khi thật đạt

---

## B4. Code slices (sau B1)

- [x] **C-1** `extract_ids` từ `music.raw_charts` → wire enrich_* *(2026-11-18)*
- [ ] **C-2** C6 models Track / AudioFeatures (+ `features_found`)
- [ ] **C-3** C4 Spotify `?ids=` + fallback (nếu Q-D ≠ 2)
- [ ] **C-4** C2 `http.py` + wire 429 Spotify/ReccoBeats
- [ ] **C-5** C10 Silver: fact + dims + LEFT JOIN + `features_found` *(hoãn)*
- [ ] **C-6** C11 Gold + coverage %
- [ ] **C-7** C12 backfill `features_found=false`
- [x] **C-8** C14 `run` Bronze-only (extract once → SP → RB); `--offline` vẫn chưa
- [ ] **C-9** C13 analytics `--report` (Nice)
- [ ] **C-10** Tests theo slice (LEFT JOIN, chunk 41, fixture offline)

---

## C. Suggested code slice order

```text
Now (Bronze Stage 4 fidelity):
  C-1 extract_ids từ raw_charts → wire enrich_*
  → C-8 run Bronze-only: extract once → enrich-spotify → enrich-reccobeats
  → DOC-3/4 diagram + Commands (logical fan-out)
  → tests fixtures Bronze payload

Later (sau Bronze ổn + Q-C):
  C-2 → C-5 Silver + features_found → C-6 Gold → C-7 backfill → …
```

Không bắt đầu Stage 5 Silver cho đến khi **D01+D02 xong** và **Q-C** có Answer.

---

## Facts vs open decisions (tóm tắt)

| Type | Statement |
|------|-----------|
| **Fact** | C7–C9 Bronze landing (ingest + enrich → `raw_*`); SoR Postgres; FS dual-write optional |
| **Fact** | Enrich ID source = **Bronze `raw_charts`** via `extract_ids` (C-1 done 18/11) |
| **Fact** | Silver / Gold / backfill / run / analytics / `http.py` / Track+AF models = stub |
| **Chốt 18/11** | Q-A=2 · Q-B=2 · Q-E=1 (hoãn D03) · Q-F=2 |
| **Open** | Q-C · Q-D · D06–D12 còn lại |
