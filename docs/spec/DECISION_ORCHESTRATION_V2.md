# Decision Record: Orchestration v2 (Airflow Option B)

**Status:** Accepted  
**Date:** 2026-11-19 (Asia/Bangkok)  
**Deciders:** Chubby  
**Supersedes:** v1 Assumption #5 (“CLI + optional OS cron; No Airflow/Prefect yet”) **for the weekly automated path**  
**Specs:** [`SPEC_V2.md`](SPEC_V2.md) · [`SPEC.md`](SPEC.md) · Self-check: [`CHECKLIST_SPEC_V2.md`](CHECKLIST_SPEC_V2.md)

---

## Context

v1 ran the medallion pipeline via CLI (`run` / stage commands). Soft items SQ-11 / GQ-8 would have grown `run.py` into Silver/Gold. Chubby chose to move **weekly schedule, retries, and week catch-up** to Airflow instead of a generic OS cron or stuffing curation into `run`.

---

## Decision

1. **Weekly orchestrator** = Airflow DAG **`spotify_weekly`** (**Option B**).
2. **Task chain:** `bronze` (`run_bronze`) → `build_silver` → `build_gold`.
3. **CLI `run` / `run_bronze`** stay **Bronze-only** (local/dev/repair). Soft **SQ-11** and **GQ-8** are **superseded** by the DAG — do not implement them inside `run.py`.
4. **Prefect** remains out of scope. **OS cron** is not the v2 happy path.
5. **C12** (`backfill-features` / `features_found=false`) stays a **separate** product — not part of `spotify_weekly`.
6. Full Phase 0 locks below are **frozen** (do not reopen without a new decision).

---

## Phase 0 locks (frozen)

| ID | Choice | Meaning |
|----|--------|---------|
| **Option B** | Locked | DAG = Bronze → Silver → Gold via existing Python builders |
| **Q1** | **A** | DAG success = all green (Bronze + Silver + Gold) |
| **Q2** | **A** | After Bronze OK, clear/retry from failed curated task only; no re-Bronze by default |
| **Q3** | **A** | Week catch-up always full chain |
| **Q4** | **A** | Two curated tasks (`build_silver` then `build_gold`) |
| **Q5** | **A** | Do not grow `run.py` with SQ-11/GQ-8 |
| **Q6** | **A** | No Gold soft_fail |
| **Q7** | **C → A** | Manual-only until Phase 4 green; then enable weekly schedule (default proposal Mon 09:00 `Asia/Bangkok`) |
| **Q8** | **A** | `chart_date` from Airflow logical / data interval via fixed week-boundary rule |
| **Q9** | **B** | Bronze re-run appends new `run_id`; consumers use latest |
| **Q10** | **A** | Catch-up MVP: `global` + `weekly_top_songs`; ~8 weeks |
| **Q11** | **A** | Airflow in Docker/separate env; not default `pyproject` deps; CI = pytest offline only |

**Traceability:** `Option B | Q1=A Q2=A Q3=A Q4=A Q5=A Q6=A Q7=C→A Q8=A Q9=B Q10=A Q11=A`

---

## Consequences

### Positive

- Clear DE portfolio story: Airflow owns schedule/retry/catch-up; Python owns fetch + builders.
- Weekly “done” = medallion all-green without manual `build-silver` / `build-gold` after each week (once Phase 4+).
- Avoids duplicate orchestration paths (`run` vs DAG) for curation.

### Trade-offs / follow-ups

- Ops bar rises (Docker/separate Airflow env).
- **Q8a LOCKED 26/11:** `chart_date` = Thứ Năm gần nhất trước `data_interval_end` (see SPEC_V2 §8).
- Catch-up (~8 × full chain) increases Charts/API/DB load — enable only after Phase 4 green (Q7).
- v1 docs that said “Airflow out of MVP” must defer to this record + `SPEC_V2.md` for weekly path.

### Non-goals (unchanged)

- Merge C12 into `spotify_weekly`
- Cloud warehouse / BI / Prefect
- Rewrite Silver/Gold as Airflow SQL operators
- Require live Airflow for default CI

---

## Assumption #5 (v1) — new wording

See [`SPEC.md`](SPEC.md) Assumptions §5. Summary:

- **Weekly path:** Airflow DAG `spotify_weekly` (this decision).
- **Local/dev:** CLI `run` Bronze-only + stage CLIs.
- **Prefect / OS cron:** not v2 happy path.

---

## Open after this decision

| ID | Item | Status |
|----|------|--------|
| **Q8a** | Week-boundary day/formula → `chart_date` | **LOCKED 26/11** — Thứ Năm gần nhất trước `data_interval_end` |
| **Q7-stage2** | Confirm Mon 09:00 Asia/Bangkok when enabling schedule | Open until Phase 5 |
| Airflow image pin | Exact Airflow 2.x in compose/image | Implementer recommendation |

---

## References

- [`SPEC_V2.md`](SPEC_V2.md) — full orchestration spec
- [`CHECKLIST_SPEC_V2.md`](CHECKLIST_SPEC_V2.md) — self-verification checklist
- [`architecture/version_2/`](../../architecture/version_2/) — v2 diagrams
