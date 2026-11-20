# Checklist: SPEC v2 Self-Verification (Airflow Option B)

**Spec:** [`SPEC_V2.md`](SPEC_V2.md) · **v1 (builders):** [`SPEC.md`](SPEC.md) · **Architecture:** [`architecture/version_2/`](../../architecture/version_2/)  
**Audience:** Chubby tự implement + tự tick  
**Status:** Phase 0 locks frozen — do not reopen Q1–Q11  
**OPEN:** **Q8a** (week-boundary day) — **không bịa weekday**; dùng **DAG params** `chart_date` cho đến khi lock  

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
- [ ] **ANTI-Q8a:** Không hard-code weekday “đoán” cho scheduled `chart_date` khi Q8a còn OPEN  
  - **Verify:** scheduled mapping hoặc còn TODO/OPEN, hoặc chỉ dùng **explicit DAG params** `chart_date` (AC-V2-8)  
- [ ] **ANTI-CI-AIRFLOW:** Default CI / `pytest` không yêu cầu Airflow container đang chạy  
  - **Verify:** `pytest -q` trên máy app env (không `docker compose` Airflow) vẫn chạy được suite mặc định  

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
  - **Verify:** `test -f docs/spec/SPEC_V2.md`  
- [x] **P1-02** v1 pointer: `SPEC.md` mentions orchestration v2 / `SPEC_V2.md`  
  - **Verify:** `rg -n "SPEC_V2" docs/spec/SPEC.md`  
- [x] **P1-03** README points to SPEC v2 for Airflow weekly path  
  - **Verify:** `rg -n "SPEC_V2|spotify_weekly|Airflow" README.md`  
- [x] **P1-04** Architecture v2 assets linked/usable  
  - **Verify:**  
    `architecture/version_2/music-pipeline-v2.0.png`  
    `architecture/version_2/music-pipeline-v2.0.drawio`  
- [x] **P1-05** Q8a documented as **OPEN** (no invented weekday)  
  - **Verify:** `rg -n "Q8a" docs/spec/SPEC_V2.md` shows OPEN  
- [x] **P1-06** Self-check checklist exists (this file)  
  - **Verify:** `test -f docs/spec/CHECKLIST_SPEC_V2.md`  
- [x] **P1-07** Decision record landed; Assumption #5 rewritten to Airflow lock  
  - **Verify:** `test -f docs/spec/DECISION_ORCHESTRATION_V2.md`  
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

- [ ] **P3-01** Task `bronze` gọi **`run_bronze`** hoặc CLI `python -m spotify_pipeline run ...`  
  - **Verify:** DAG/operator — import `run_bronze` **hoặc** Bash/CLI `run`  
- [ ] **P3-02** Watermark: **DAG params/conf `chart_date`** (và type/country) khi Q8a OPEN  
  - **Verify:** trigger manual với conf:  
    `{"chart_date":"YYYY-MM-DD","chart_type":"weekly_top_songs","country":"global"}`  
    Task log in watermark đúng — **không** dựa weekday bịa  
- [ ] **P3-03** Defaults MVP: `weekly_top_songs` + `global` (Q10)  
  - **Verify:** code default hoặc docs operator  
- [ ] **P3-04** Manual trigger: Bronze task **success** cho một `chart_date` biết trước  
  - **Verify:** UI task `bronze` = success; và/hoặc SQL có `music.raw_*` mới  
- [ ] **P3-05** Airflow retries trên Bronze **và** client 429 vẫn còn trong app  
  - **Verify:** `retries=` / `default_args` trong DAG; `rg -n "Retry-After|429" src/spotify_pipeline/clients/`  

### Phase 3 DoD / AC

- [ ] **DoD-P3:** Một watermark Bronze xong qua DAG, reuse `run_bronze`, params path tôn trọng Q8a OPEN  
  - **Verify:** P3-01 + P3-02 + P3-04  

---

## Phase 4 — Silver / Gold tasks (Option B core) + Smoke card

### Checks

- [ ] **P4-01** Task graph: `bronze >> build_silver >> build_gold` (Q4=A)  
  - **Verify:** đọc DAG; UI Graph View 3 tasks nối tiếp  
- [ ] **P4-02** Silver gọi **`build_silver`** / CLI `build-silver` — không HTTP  
  - **Verify:** code call + (optional) log không gọi Charts/Spotify/ReccoBeats  
- [ ] **P4-03** Gold gọi **`build_gold`** / CLI `build-gold`  
  - **Verify:** tương tự P4-02  
- [ ] **P4-04** Gold **không** `soft_fail=True` (Q6=A)  
  - **Verify:** `rg -n "soft_fail" dags/` → không soft_fail Gold  
- [ ] **P4-05** All-green: DAG run success chỉ khi cả 3 tasks success (Q1=A)  
  - **Verify:** UI DAG Run = **success** iff bronze+silver+gold success  
- [ ] **P4-06** Recovery demo (Q2=A): fail Gold/Silver → Clear **failed task only** → success; Bronze **không** chạy lại  
  - **Verify:** Task try history — Bronze try count không tăng trong recovery đó  
- [ ] **P4-07** `run.py` vẫn Bronze-only  
  - **Verify:** ANTI-RUN lại  

### Smoke card — one watermark all-green

```text
SMOKE — spotify_weekly (manual)
chart_date:  ____________   (explicit param; Q8a OPEN)
chart_type:  weekly_top_songs
country:     global

[ ] Trigger DAG run with conf/params above
[ ] bronze       = success   (run_bronze)
[ ] build_silver = success
[ ] build_gold   = success
[ ] DAG run      = success   (all green)
[ ] Spot-check DB: raw_* latest + fact_chart / gold outputs for watermark
[ ] Did NOT invent Q8a weekday for this smoke
```

### Phase 4 DoD / AC

- [ ] **DoD-P4 / AC-V2-2:** Manual full chain OK với builders hiện có  
- [ ] **AC-V2-3:** Recovery from failed curated task — P4-06  
- [ ] **AC-V2-4:** Fail bất kỳ task → DAG không success; no Gold soft_fail  
- [ ] **AC-V2-5:** CLI `run` vẫn Bronze-only  
  - **Verify thêm:** `python -m spotify_pipeline run --help`  

**GATE:** Không sang Phase 5 nếu DoD-P4 chưa xanh (Q7).

---

## Phase 5 — Schedule rồi Catch-up (Q7 → Q3/Q9/Q10)

### 5A — Enable schedule (chỉ sau Phase 4)

- [ ] **P5-01** Confirm/override timetable: default proposal **Mon 09:00 `Asia/Bangkok`** (Q7 stage 2)  
  - **Verify:** DAG `schedule` + timezone; ghi đè nếu chọn khác  
- [ ] **P5-02** Scheduled `chart_date` mapping: **chỉ** sau Q8a locked — hoặc còn phụ thuộc params/OPEN  
  - **Verify:** nếu Q8a OPEN → không ship weekday “im lặng”; AC-V2-8  
- [ ] **P5-03** Ít nhất một run sau khi enable schedule được ghi nhận  
  - **Verify:** Airflow UI next run / history  

### 5B — Week catch-up (~8 weeks, full chain)

- [ ] **P5-04** Scope = `global` + `weekly_top_songs` + ~8 weeks (Q10=A)  
  - **Verify:** docs/runbook hoặc backfill params  
- [ ] **P5-05** Mỗi tuần catch-up = **full chain** (Q3=A)  
  - **Verify:** ≥2 tuần mẫu — mỗi tuần đủ 3 tasks  
- [ ] **P5-06** Bronze append (Q9=B): re-process → `run_id` mới; curated dùng latest  
  - **Verify:** DB — 2 raw rows khác `run_id` cùng watermark; silver vẫn OK  
- [ ] **P5-07** Naming: **week catch-up** ≠ C12 / `backfill-features`  
  - **Verify:** docs tách hai khái niệm  

### Phase 5 DoD / AC

- [ ] **DoD-P5 / AC-V2-6:** ~8 tuần global songs full chain; không phải C12  
- [ ] Schedule chỉ bật sau Phase 4 (Q7)  

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
| 3 Bronze | [ ] | [ ] | params path if Q8a OPEN |
| 4 Silver/Gold + smoke | [ ] | [ ] | **GATE for P5** |
| 5 Schedule + catch-up | [ ] | [ ] | Q7 then Q3/Q10 |
| 6 CI | [ ] | [ ] | |
| 7 Runbook | [ ] | [ ] | |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-11-19 | Initial self-verification checklist for SPEC_V2 Option B (Phases 1–7, Q1–Q11 audit, anti-checks, smoke card). Q8a left OPEN. Phase 1 pre-ticked after SPEC_V2 land. |
