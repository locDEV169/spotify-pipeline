# Airflow ops (SPEC v2 Phase 3)

**DAG:** `spotify_weekly` · **Spec:** [`docs/spec/SPEC_V2.md`](../spec/SPEC_V2.md) · **Q11=A:** Airflow runs in Docker, **not** in default `pyproject` deps.

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

`src/` is copied into the image, not mounted. Rebuild after any change under `src/`.

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

## Manual trigger (Phase 3)

`bronze` calls `run_bronze` for one watermark. `build_silver` and `build_gold` are still `EmptyOperator` placeholders (Phase 4). `schedule=None` (Q7 stage 1 — manual only).

Trigger with conf (Q8a still OPEN — pass `chart_date` explicitly):

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
- The DAG calls `run_bronze(write_fs=False)`. Bronze is written to Postgres only. The container does not write `data/bronze` files.

## Stop

```bash
docker compose -f docker/airflow/docker-compose.yml down
```

## Anti-checks

- Do **not** `pip install apache-airflow` into the app `.venv` for normal development.
- App tests: `pytest -q` without starting this compose.
- Do **not** merge C12 feature backfill into this DAG.
