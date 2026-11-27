# Airflow ops (SPEC v2 Phase 3–4)

**DAG:** `spotify_weekly` · **Spec:** [`docs/spec/v2/SPEC_V2.md`](../spec/v2/SPEC_V2.md) · **Q11=A:** Airflow runs in Docker, **not** in default `pyproject` deps.

## Prerequisites

- Docker + Docker Compose
- Repo `.env` with `SUPABASE_DB_URL` and Spotify client credentials (the `bronze` task runs the app and fails without them)
- Never commit `.env`

## Build and start

The image is built from the repo root by `docker/airflow/Dockerfile`. It installs the app package using Airflow 2.9.3 constraints. Airflow itself is not in the app `pyproject.toml`.

```bash
# from repo root
docker compose -f docker/airflow/docker-compose.yml up -d --build
docker compose -f docker/airflow/docker-compose.yml logs -f airflow
```

`src/` and `docs/sql/` are copied into the image, not mounted (Silver/Gold load SQL templates from `<repo root>/docs/sql`). Rebuild after any change under `src/` or `docs/sql/`.

On Windows Docker Desktop, `docker compose ... build` may exit 0 without building (buildx bake asks for filesystem privileges). If that happens, build directly and start without rebuilding:

```bash
docker build -f docker/airflow/Dockerfile -t spotify-pipeline-airflow:local .
docker compose -f docker/airflow/docker-compose.yml up -d --no-build
```

On first boot, `airflow standalone` prints an **admin password** in the logs.  
UI: [http://localhost:8080](http://localhost:8080) · user `admin`.

## Verify DAG

```bash
docker compose -f docker/airflow/docker-compose.yml exec airflow airflow dags list
# expect: spotify_weekly
```

UI → DAGs → `spotify_weekly` (may start **paused** — unpause to trigger).

## Manual trigger (Phase 3–4)

Chain: `bronze >> build_silver >> build_gold`, all for the same watermark. `bronze` calls `run_bronze`; `build_silver` / `build_gold` call the library builders (DB only, no HTTP). The DAG run is green only when all three succeed. If a task fails, downstream does not run — fix the cause, then **Clear** the failed task (with downstream, not upstream) so Bronze is not re-run. The weekly schedule is on (see **Schedule** below); manual triggers still work.

Trigger with conf (manual trigger: pass `chart_date` explicitly; scheduled runs derive it from Q8a = Thứ Năm gần nhất trước `data_interval_end`, see SPEC_V2 §8):

```json
{
  "chart_date": "2026-11-19",
  "chart_type": "weekly_top_songs",
  "country": "global"
}
```

Rules:

- `chart_type` and `country` default to `weekly_top_songs` and `global`.
- `chart_date` must be the **live** Charts `public/v0` date at trigger time. Charts only serves the current week. Any other date fails the `bronze` task with `live chart watermark mismatch` and writes nothing. The task log shows the live date as `live=(...)`.
- An empty `chart_date` fails with `chart_date is required (YYYY-MM-DD)`.
- `bronze` has `retries=1` with a 5-minute delay. A retry re-runs ingest and appends rows under a new `run_id` (Q9=B).
- `build_silver` / `build_gold` have `retries=1` with a 1-minute delay (idempotent upserts / read-only views).
- `build_silver` reads the **latest** Bronze for the watermark. `build_gold` only reads Silver views; with no Silver rows it would report zeros, so check `chart_rows > 0` in its log.
- The DAG calls `run_bronze(write_fs=False)`. Bronze is written to Postgres only. The container does not write `data/bronze` files.

## Schedule (Phase 5)

- **Timetable:** Mon 09:00 `Asia/Bangkok` (`0 9 * * 1`), `catchup=False`, `max_active_runs=1`. Unpause the DAG once (`airflow dags unpause spotify_weekly`); a recreated container starts paused again and loses run history.
- **Watermark:** a scheduled run uses `chart_date` = the most recent Thursday before `data_interval_end` (Q8a; Mon 30/11 → Thu 26/11). An explicit `chart_date` in conf always wins. A manual run with an empty `chart_date` fails with `chart_date is required`.
- **The Docker host must be running** at Mon 09:00; a missed run is not re-created (`catchup=False`).
- **No history back-fill:** Charts `public/v0` only serves the live week, so the 8 weeks accumulate one scheduled run at a time. If the Charts live date is not the derived Thursday when the run fires, `bronze` fails with `live chart watermark mismatch` and writes nothing — re-run manually with the live date.
- **Week catch-up ≠ C12:** week catch-up = more weekly watermarks through this DAG (full chain). C12 feature backfill (re-query ReccoBeats where `features_found=false`) is **not** in this DAG.

## Ops tables (SPEC_V2 §19b)

Apply the DDL **before** deploying a DAG that writes `music.pipeline_runs` (a missing table only logs a warning, tasks still run):

```bash
python scripts/ddl/apply_music_ddl.py   # from the host; idempotent
```

Then rebuild the image (`src/` changed) and recreate the container (see **Build and start**; re-unpause the DAG).

```sql
SELECT * FROM music.ops_pipeline_health ORDER BY chart_date DESC;   -- per watermark: coverage, silver_stale, bronze_age
SELECT dag_run_id, status, current_task, error_task, error_message, started_at, finished_at
FROM music.pipeline_runs ORDER BY started_at DESC LIMIT 10;
```

- One row per DAG run; a retry or **Clear** moves the same row failed → running → success. `summary` holds each task's result and its own `run_id` (layers do not share one id).
- `failed` is written after the **last** retry only. `error_message` has DB URIs redacted.
- A row stuck in `running` means the worker was killed or the task was marked success in the UI ("Mark success" bypasses the Ops writes). Clear the task or ignore the row.
- Ops writes are best-effort: check the task log for `ops pipeline_runs write skipped` warnings if a row is missing.
- The image installs the app **without `flask`** (only `src/spotify_pipeline/api` uses it; Airflow 2.9.3 pins flask 2.2.5).

## Stop

```bash
docker compose -f docker/airflow/docker-compose.yml down
```

## Anti-checks

- Do **not** `pip install apache-airflow` into the app `.venv` for normal development.
- App tests: `pytest -q` without starting this compose.
- Do **not** merge C12 feature backfill into this DAG.
