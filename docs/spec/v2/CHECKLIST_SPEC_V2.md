# Checklist: SPEC v2 Self-Verification (Airflow Option B)

**Spec:** [`SPEC_V2.md`](SPEC_V2.md) · **v1 (builders):** [`SPEC.md`](../SPEC.md) · **Architecture:** [`architecture/version_2/`](../../../architecture/version_2/)  
**Audience:** Chubby tự implement + tự tick  
**Status:** Phase 0 locks frozen — do not reopen Q1–Q11  
**LOCKED 26/11:** **Q8a** = Thứ Năm gần nhất trước `data_interval_end` (SPEC §8). Trước khi code P5-02 cần verify công thức đó trên Airflow  

**Cách dùng:** Làm tuần tự Phase 1 → 7. Tick `- [x]` chỉ khi **How to verify** đã pass. Đừng bật Phase 5 trước khi Phase 4 DoD xanh (Q7).

---

## 0. Anti-checks / Non-goals (tick suốt quá trình)

Làm sai một dòng dưới đây = fail SPEC v2 dù DAG “chạy được”.

- [ ] **ANTI-C12:** DAG `spotify_weekly` **không** gọi / không đặt tên task kiểu feature backfill C12  
  - **Verify:** đọc `dags/**/*.py` (hoặc path DAG đã chọn) — không có `backfill-features` / `features_found=false` repair trong DAG weekly  
- [ ] **ANTI-DEPS:** `apache-airflow` (và extras Airflow) **không** nằm trong default `[project].dependencies` của `pyproject.toml`  
  - **Verify:** `rg -n "airflow" pyproject.toml` → không có trong deps chính (Q11=A)  
- [ ] **ANTI-RUN:** `src/spotify_pipeline/pipeline/run.py` **không** gọi `build_silver` / `build_gold`  
  - **Verify:** `rg -n "build_silver|build_gold" src/spotify_pipeline/pipeline/run.py` → 0 matches (Q5=A)  
- [ ] **ANTI-SQL-ORCH:** Không rewrite Silver/Gold thành Airflow SQL operators thay builders  
  - **Verify:** curated tasks import/call `build_silver` / `build_gold` (hoặc CLI tương đương), không `SQLExecuteQueryOperator` thay thế medallion  
- [ ] **ANTI-Q8a:** Scheduled `chart_date` chỉ theo công thức Q8a đã khóa (Thứ Năm trước `data_interval_end`); không weekday nào khác được hard-code  
  - **Verify:** `rg -n "chart_date_before" dags/ src/` — mapping chỉ ở một nơi; manual dùng **explicit DAG params** `chart_date` (AC-V2-8)  
- [ ] **ANTI-CI-AIRFLOW:** Default CI / `pytest` không yêu cầu Airflow container đang chạy  
  - **Verify:** `pytest -q` trên máy app env (không `docker compose` Airflow) vẫn chạy được suite mặc định  
- [ ] **ANTI-OPS-GATE:** Ops ([SPEC §19b](SPEC_V2.md)) chỉ quan sát: không task mới, không `soft_fail` / `trigger_rule`, ghi Ops lỗi không làm fail task  
  - **Verify:** `rg -n "soft_fail|trigger_rule" dags/` → 0 matches; `pytest tests/test_pipeline_ops.py` (test "write failure never raises")  
- [x] **OPS-01** `music.pipeline_runs` + `music.ops_pipeline_health` có trong `music_schema.sql`, apply idempotent  
  - **Verify:** `pytest tests/test_apply_music_ddl.py`; `SELECT * FROM music.ops_pipeline_health`  
- [x] **OPS-02** Run DAG thật → đúng 1 row `pipeline_runs` (`success`, `summary` có `bronze`/`build_silver`/`build_gold`)  
  - **Evidence (26/11):** manual run `ops_live_ok` (chart_date 2026-11-19) → 1 row, status=success  

---

## 1. Decision audit card (Q1–Q11) — audit drift

Tick khi implementation **khớp** lock (không “gần đúng”).

| Lock | Meaning | Checklist proof | Done |
|------|---------|-----------------|------|
| **Option B** | Bronze → Silver → Gold in DAG | Task graph `bronze >> build_silver >> build_gold` | [ ] |
| **Q1=A** | All green | Không coi run success nếu Gold fail; không soft_fail Gold | [ ] |
| **Q2=A** | Clear from failed task | Runbook/UI: retry Silver/Gold không auto re-Bronze | [ ] |
| **Q3=A** | Catch-up full chain | Catch-up config/docs: mỗi tuần đủ 3 tasks | [ ] |
| **Q4=A** | Two curated tasks | Hai task riêng (không gộp một `curate`) | [ ] |
| **Q5=A** | `run` Bronze-only | ANTI-RUN pass + CLI `run` docstring/behavior Bronze | [ ] |
| **Q6=A** | No Gold soft_fail | Task Gold: fail = failed (không `soft_fail=True`) | [ ] |
| **Q7=C→A** | Manual then schedule | `schedule=None` (hoặc tương đương) đến khi Phase 4 DoD; rồi mới bật timetable | [ ] |
| **Q8=A** | Logical/data interval → chart_date | Code/docs nêu mapping rule; **Q8a** vẫn OPEN hoặc đã lock riêng | [ ] |
| **Q9=B** | Append `run_id` / latest | Bronze re-run tạo `run_id` mới; Silver đọc latest | [ ] |
| **Q10=A** | Catch-up scope | Docs/config: `global` + `weekly_top_songs` + ~8 weeks | [ ] |
| **Q11=A** | Docker/separate + offline CI | ANTI-DEPS + ANTI-CI-AIRFLOW + compose/env riêng tồn tại | [ ] |

**One-liner freeze:**  
`Option B | Q1=A Q2=A Q3=A Q4=A Q5=A Q6=A Q7=C→A Q8=A Q9=B Q10=A Q11=A`

---

## Phase 1 — Docs (SPEC land)

### Checks

- [x] **P1-01** File [`SPEC_V2.md`](SPEC_V2.md) exists and describes Option B + Q1–Q11  
  - **Verify:** `test -f docs/spec/v2/SPEC_V2.md`  
- [x] **P1-02** v1 pointer: `SPEC.md` mentions orchestration v2 / `SPEC_V2.md`  
  - **Verify:** `rg -n "SPEC_V2" docs/spec/SPEC.md`  
- [x] **P1-03** README points to SPEC v2 for Airflow weekly path  
  - **Verify:** `rg -n "SPEC_V2|spotify_weekly|Airflow" README.md`  
- [x] **P1-04** Architecture v2 assets linked/usable  
  - **Verify:**  
    `architecture/version_2/music-pipeline-v2.0.png` (19/11 proposal)  
    `architecture/version_2/music-pipeline-v2.0.drawio` (19/11 proposal)  
    `architecture/version_2/music-pipeline-v2.1.drawio` (26/11 as-built + BACKLOG)  
- [x] **P1-05** Q8a documented as **OPEN** (no invented weekday)  
  - **Verify:** `rg -n "Q8a" docs/spec/v2/SPEC_V2.md` shows OPEN  
- [x] **P1-06** Self-check checklist exists (this file)  
  - **Verify:** `test -f docs/spec/v2/CHECKLIST_SPEC_V2.md`  
- [x] **P1-07** Decision record landed; Assumption #5 rewritten to Airflow lock  
  - **Verify:** `test -f docs/spec/v2/DECISION_ORCHESTRATION_V2.md`  
  - **Verify:** `rg -n "Orchestration \\(locked 2026-11-19" docs/spec/SPEC.md`  

### Phase 1 DoD / AC

- [x] **DoD-P1 / AC-V2-1:** Doc relationship clear — v2 overrides v1 “No Airflow” for weekly orchestration  
  - **Verify:** § Relationship + Assumptions trong `SPEC_V2.md`; Assumption #5 + [`DECISION_ORCHESTRATION_V2.md`](DECISION_ORCHESTRATION_V2.md); README nêu Airflow locked in SPEC v2 (not coded yet)  

---

## Phase 2 — Airflow skeleton (Q11)

### Checks

- [x] **P2-01** DAG file exists with `dag_id="spotify_weekly"` (path có thể `dags/spotify_weekly.py`)  
  - **Verify:** `rg -n "spotify_weekly" dags/ --glob "*.py"` (hoặc path đã chọn)  
- [x] **P2-02** Airflow runtime qua Docker Compose **hoặc** env/docs riêng (không nhét vào default app install)  
  - **Verify:** tồn tại `docker-compose*.yml` / `docker/` / runbook Airflow **và** ANTI-DEPS pass  
- [x] **P2-03** DAG xuất hiện trong Airflow UI (local)  
  - **Verify:** UI → DAGs → `spotify_weekly` (hoặc `airflow dags list | rg spotify_weekly`)  
- [x] **P2-04** Stage-1 schedule: manual-only (`schedule=None` / không timetable)  
  - **Verify:** đọc DAG — `schedule` = `None` (Q7 stage 1)  
- [x] **P2-05** Worker/container inject secrets (`.env`) — không commit secrets  
  - **Verify:** `.env` trong `.gitignore`; compose/docs mention env  

### Phase 2 DoD / AC

- [x] **DoD-P2:** Skeleton parse được + UI list DAG; app `pytest` vẫn chạy **không** cần Airflow up  
  - **Verify:** Airflow UI list OK **và** (app venv) `pytest -q`  

---

## Phase 3 — Bronze task (`run_bronze`)

### Checks

- [x] **P3-01** Task `bronze` gọi **`run_bronze`** hoặc CLI `python -m spotify_pipeline run ...`  
  - **Verify:** DAG/operator — import `run_bronze` **hoặc** Bash/CLI `run`  
  - **Evidence (26/11):** `dags/spotify_weekly.py` — `PythonOperator` `bronze` gọi `run_bronze(watermark, write_fs=False)`; DagBag parse không lỗi, `bronze` là `PythonOperator`
- [x] **P3-02** Watermark: **DAG params/conf `chart_date`** (và type/country) khi Q8a OPEN  
  - **Verify:** trigger manual với conf:  
    `{"chart_date":"YYYY-MM-DD","chart_type":"weekly_top_songs","country":"global"}`  
    Task log in watermark đúng — **không** dựa weekday bịa  
  - **Evidence (26/11):** run `smoke_p4_20261119` conf `chart_date=2026-11-19`; log `bronze watermark=('2026-11-19', 'weekly_top_songs', 'global')`. Live date đọc từ Charts, không bịa weekday  
- [x] **P3-03** Defaults MVP: `weekly_top_songs` + `global` (Q10)  
  - **Verify:** code default hoặc docs operator  
  - **Evidence (26/11):** DAG params defaults + `docs/ops/AIRFLOW.md` "Manual trigger (Phase 3)"  
- [x] **P3-04** Manual trigger: Bronze task **success** cho một `chart_date` biết trước  
  - **Verify:** UI task `bronze` = success; và/hoặc SQL có `music.raw_*` mới  
  - **Evidence (26/11):** `bronze` = success (~47s); `raw_charts` 0→1 dòng cho 2026-11-19; summary: 50 entries, Spotify inserted 108, ReccoBeats hits 33 / misses 17  
- [x] **P3-05** Airflow retries trên Bronze **và** client 429 vẫn còn trong app  
  - **Verify:** `retries=` / `default_args` trong DAG; `rg -n "Retry-After|429" src/spotify_pipeline/clients/`  
  - **Evidence (26/11):** `bronze` `retries=1`, `retry_delay=5min`. 429 + `Retry-After` còn ở `clients/reccobeats.py`. **Gap G8:** Spotify/Charts client chưa có 429 retry, `clients/http.py` vẫn stub (không thuộc checklist Phase 3)  

### Phase 3 DoD / AC

- [x] **DoD-P3:** Một watermark Bronze xong qua DAG, reuse `run_bronze`, params path tôn trọng Q8a OPEN  
  - **Verify:** P3-01 + P3-02 + P3-04  

---

## Phase 4 — Silver / Gold tasks (Option B core) + Smoke card

### Checks

- [x] **P4-01** Task graph: `bronze >> build_silver >> build_gold` (Q4=A)  
  - **Verify:** đọc DAG; UI Graph View 3 tasks nối tiếp  
  - **Evidence (26/11):** `airflow tasks list spotify_weekly --tree` → bronze → build_silver → build_gold; DagBag import_errors rỗng  
- [x] **P4-02** Silver gọi **`build_silver`** / CLI `build-silver` — không HTTP  
  - **Verify:** code call + (optional) log không gọi Charts/Spotify/ReccoBeats  
  - **Evidence (26/11):** `_build_silver_task` → `build_silver(watermark)`; `tasks test` với DB URL rỗng → `SilverError` (task fail, không ghi). Smoke run `smoke_p4_20261119`: log `build_silver` / `build_gold` không có dòng `HTTP Request`  
- [x] **P4-03** Gold gọi **`build_gold`** / CLI `build-gold`  
  - **Verify:** tương tự P4-02  
  - **Evidence (26/11):** `tasks test build_gold` (chart_date 2026-11-12, chỉ đọc) → SUCCESS, `chart_rows=50`, `features_found_rows=32` (64%). Cần `docs/sql` trong image (Dockerfile đã sửa)  
- [x] **P4-04** Gold **không** `soft_fail=True` (Q6=A)  
  - **Verify:** `rg -n "soft_fail" dags/` → không soft_fail Gold  
  - **Evidence (26/11):** `rg "soft_fail|trigger_rule" dags/` → không có  
- [x] **P4-05** All-green: DAG run success chỉ khi cả 3 tasks success (Q1=A)  
  - **Verify:** UI DAG Run = **success** iff bronze+silver+gold success  
  - **Evidence (26/11):** run `smoke_p4_20261119` = success, 3 task success. Chiều ngược (fail → DAG không success) chưa chứng minh bằng DAG run, xem P4-06 / AC-V2-4  
- [x] **P4-06** Recovery demo (Q2=A): fail Gold/Silver → Clear **failed task only** → success; Bronze **không** chạy lại  
  - **Verify:** Task try history — Bronze try count không tăng trong recovery đó
  - **Evidence (26/11, run `smoke_p4_20261119`):** chèn `raise` tạm vào `_build_silver_task` → `build_silver` failed, `build_gold` upstream_failed, run **failed**. Khôi phục file (sha256 khớp backup), clear `build_silver` rồi `build_gold` → cả hai success, run **success**. `bronze` chỉ có `attempt=1.log`; `raw_charts` = 1 dòng (không đổi)  
- [x] **P4-07** `run.py` vẫn Bronze-only  
  - **Verify:** ANTI-RUN lại  
  - **Evidence (26/11):** `rg "build_silver|build_gold" src/spotify_pipeline/pipeline/run.py` → không có  

### Smoke card — one watermark all-green

```text
SMOKE — spotify_weekly (manual)
chart_date:  2026-11-19     (explicit param; Q8a OPEN)
chart_type:  weekly_top_songs
country:     global

[x] Trigger DAG run with conf/params above   (run_id smoke_p4_20261119, 26/11)
[x] bronze       = success   (run_bronze)
[x] build_silver = success   (fact 50, dim_track 50, artists 58, bridges 65)
[x] build_gold   = success   (chart_rows 50, features_found 33 = 66%)
[x] DAG run      = success   (all green)
[x] Spot-check DB: raw_charts 1, fact_chart 50, gold_feature_coverage 50/33/66.00
[x] Did NOT invent Q8a weekday for this smoke (chart_date 2026-11-19 = live Charts date)
```

### Phase 4 DoD / AC

- [x] **AC-V2-2:** Manual full chain OK với builders hiện có (smoke `smoke_p4_20261119`)  
- [x] **DoD-P4:** Gate để sang Phase 5 — P4-06 + AC-V2-3 + AC-V2-4 đã xanh (26/11)  
- [x] **AC-V2-3:** Recovery from failed curated task — P4-06  
- [x] **AC-V2-4:** Fail bất kỳ task → DAG không success; no Gold soft_fail  
  - **Evidence (26/11):** `build_silver` fail → DAG run `failed`; `rg "soft_fail|trigger_rule" dags/` không có  
- [x] **AC-V2-5:** CLI `run` vẫn Bronze-only  
  - **Verify thêm:** `python -m spotify_pipeline run --help`  
  - **Evidence (26/11):** help ghi "Silver/Gold/report still deferred"; `run.py` không gọi silver/gold  

**GATE:** Không sang Phase 5 nếu DoD-P4 chưa xanh (Q7).

---

## Phase 5 — Schedule rồi Catch-up (Q7 → Q3/Q9/Q10)

### Gate (chặn Phase 5)

- [x] **P5-G1** Phase 4 gate đã xanh (P4-06, AC-V2-3/4) — evidence ở P4-06  
- [x] **P5-G2** Q8a: **locked** = Thứ Năm gần nhất trước `data_interval_end` (Chubby, 26/11), đã ghi SPEC §8. *Còn lại:* verify trên run thật ở P5-02  
- [x] **P5-G3** Nguồn lịch sử: **tích lũy dần** — schedule capture từng tuần live; không thêm nguồn, không ingest tuần cũ (public/v0 từ chối)  
- [x] **P5-G4** Timetable Mon 09:00 `Asia/Bangkok` (Q7 stage 2) — Chubby xác nhận 26/11  

### 5A — Enable schedule (chỉ sau Phase 4)

- [x] **P5-01** Confirm/override timetable: default proposal **Mon 09:00 `Asia/Bangkok`** (Q7 stage 2)  
  - **Verify:** DAG `schedule` + timezone; ghi đè nếu chọn khác  
  - **Evidence (26/11):** DagBag → `schedule=0 9 * * 1`, tz `Asia/Bangkok`, `catchup=False`, `max_active_runs=1`; `airflow dags next-execution` → logical 2026-11-23/30, 12-07 (02:00 UTC = 09:00 Bangkok); DAG unpaused, không tạo run ngay  
- [ ] **P5-02** Scheduled `chart_date` mapping theo **Q8a = Thứ Năm gần nhất trước `data_interval_end`**; manual không có chart_date phải fail rõ  
  - **Verify:** công thức đúng trong code + test; **run theo lịch thật** (Mon 30/11) log `bronze watermark=('2026-11-26', ...)` và không `live chart watermark mismatch`  
  - **Evidence một phần (26/11):** `chart_date_before` + test (112 pass); DagBag + context giả: scheduled → `2026-11-26`, explicit param thắng, manual rỗng → `chart_date is required`. **Chưa tick:** còn chờ run thật  
- [ ] **P5-03** Ít nhất một run sau khi enable schedule được ghi nhận  
  - **Verify:** Airflow UI next run / history  

### 5B — Week catch-up (~8 weeks, full chain)

- [ ] **P5-04** Scope = `global` + `weekly_top_songs` + ~8 tuần **tích lũy dần** từ schedule (Q10=A; không catch-up lịch sử)  
  - **Lưu ý:** 8 tuần là thời gian thực, không xong ngay sau khi bật schedule  
  - **Verify:** docs/runbook hoặc backfill params  
- [ ] **P5-05** Mỗi tuần catch-up = **full chain** (Q3=A)  
  - **Verify:** ≥2 tuần mẫu — mỗi tuần đủ 3 tasks  
- [ ] **P5-06** Bronze append (Q9=B): re-process → `run_id` mới; curated dùng latest  
  - **Verify:** DB — 2 raw rows khác `run_id` cùng watermark; silver vẫn OK  
- [x] **P5-07** Naming: **week catch-up** ≠ C12 / `backfill-features`  
  - **Verify:** docs tách hai khái niệm  

- [ ] **P5-08** Rate limit: `max_active_runs=1` (chạy tuần tự); quyết định G8 (429 Spotify) trước khi tích lũy nhiều run  
  - **Verify:** `rg "max_active_runs" dags/`; log không có 429 lặp lại  
  - **Evidence một phần (26/11):** `max_active_runs=1` đã set. **Chưa tick:** G8 (Spotify/Charts chưa có 429 retry) chưa quyết; mỗi run ~108 call Spotify, 1 run/tuần nên rủi ro thấp  

### Phase 5 DoD / AC

- [ ] **DoD-P5 / AC-V2-6:** ~8 tuần global songs full chain (tích lũy dần từ schedule); không phải C12  
- [x] Schedule chỉ bật sau Phase 4 (Q7) — bật 26/11, sau khi DoD-P4 xanh cùng ngày  

---

## Phase 6 — CI / packaging boundary (Q11)

### Checks

- [ ] **P6-01** `pytest -q` xanh trên app env **không** start Airflow  
  - **Verify:** chạy lệnh; exit 0  
- [ ] **P6-02** Default `pyproject` deps không có Airflow  
  - **Verify:** ANTI-DEPS  
- [ ] **P6-03** (Nếu có CI workflow) job mặc định không bắt buộc Airflow service  
  - **Verify:** đọc `.github/workflows/*` hoặc CI config  
- [ ] **P6-04** Offline/fixture path Bronze CLI không bị phá  
  - **Verify:** `rg -n "offline" src/spotify_pipeline/cli.py` — nếu `run --offline` vẫn open từ v1 thì ghi chú, không block orchestration  

### Phase 6 DoD / AC

- [ ] **DoD-P6 / AC-V2-7:** Default CI/pytest offline without Airflow runtime  

---

## Phase 7 — Docs / runbook

### Checks

- [ ] **P7-01** README: lên Airflow (Docker/separate), trigger manual, params `chart_date`  
- [ ] **P7-02** Runbook Q2: clear from failed Silver/Gold; không re-Bronze mặc định  
- [ ] **P7-03** Q7 stages documented (manual → schedule)  
- [ ] **P7-04** C12 vs week catch-up glossary  
- [ ] **P7-05** Link architecture v2 + `SPEC_V2.md`  
- [ ] **P7-06** Decision audit card (§1) all ticked  

### Phase 7 DoD / AC

- [ ] **DoD-P7:** Làm lại smoke card chỉ từ docs  

---

## End-to-end acceptance map (SPEC_V2 §18)

| AC | Phase | Self-check |
|----|-------|------------|
| AC-V2-1 Spec relationship | P1 | DoD-P1 |
| AC-V2-2 Manual full chain | P4 | Smoke card |
| AC-V2-3 Failure recovery | P4 | P4-06 |
| AC-V2-4 Success / no soft_fail | P4 | P4-04, P4-05 |
| AC-V2-5 `run` Bronze-only | P4 + anti | ANTI-RUN, P4-07 |
| AC-V2-6 Catch-up | P5 | P5-04…P5-07 |
| AC-V2-7 CI | P6 | P6-01…P6-03 |
| AC-V2-8 Q8a discipline | P3–P5 | ANTI-Q8a, P3-02, P5-02 |

---

## Progress tracker

| Phase | Started | DoD met | Notes |
|-------|---------|---------|-------|
| 1 Docs | [x] | [x] | SPEC_V2 + pointers + this checklist (2026-11-19) |
| 2 Skeleton | [x] | [x] | `dags/` + `docker/airflow/` + `docs/ops/AIRFLOW.md` (2026-11-19) |
| 3 Bronze | [x] | [x] | Smoke 26/11: `bronze` success cho 2026-11-19 (run `smoke_p4_20261119`) |
| 4 Silver/Gold + smoke | [x] | [x] | Smoke all-green + recovery P4-06 xanh (26/11). Gate P5 mở |
| 5 Schedule + catch-up | [x] | [ ] | Schedule bật 26/11 (P5-01, P5-07). Chờ run thật Mon 30/11 09:00 cho P5-02/03; P5-04..06 + DoD tích lũy ~8 tuần; G8 mở |
| 6 CI | [ ] | [ ] | |
| 7 Runbook | [ ] | [ ] | |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-11-19 | Initial self-verification checklist for SPEC_V2 Option B (Phases 1–7, Q1–Q11 audit, anti-checks, smoke card). Q8a left OPEN. Phase 1 pre-ticked after SPEC_V2 land. |
