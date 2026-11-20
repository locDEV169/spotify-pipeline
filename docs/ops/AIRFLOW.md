# Airflow ops (SPEC v2 Phase 2)

**DAG:** `spotify_weekly` · **Spec:** [`docs/spec/SPEC_V2.md`](../spec/SPEC_V2.md) · **Q11=A:** Airflow runs in Docker, **not** in default `pyproject` deps.

## Prerequisites

- Docker + Docker Compose
- Repo `.env` optional for Phase 2 (skeleton tasks do not call APIs yet)
- Never commit `.env`

## Start

```bash
# from repo root
docker compose -f docker/airflow/docker-compose.yml up -d
docker compose -f docker/airflow/docker-compose.yml logs -f airflow
```

On first boot, `airflow standalone` prints an **admin password** in the logs.  
UI: [http://localhost:8080](http://localhost:8080) · user `admin`.

## Verify DAG

```bash
docker compose -f docker/airflow/docker-compose.yml exec airflow airflow dags list
# expect: spotify_weekly
```

UI → DAGs → `spotify_weekly` (may start **paused** — unpause to trigger).

## Manual trigger (Phase 2)

Phase 2 tasks are `EmptyOperator` placeholders (`bronze` → `build_silver` → `build_gold`).  
`schedule=None` (Q7 stage 1 — manual only).

Trigger with conf (Q8a still OPEN — pass `chart_date` explicitly):

```json
{
  "chart_date": "2026-11-12",
  "chart_type": "weekly_top_songs",
  "country": "global"
}
```

Params are defined on the DAG; wiring into Python builders starts in Phase 3.

## Stop

```bash
docker compose -f docker/airflow/docker-compose.yml down
```

## Anti-checks

- Do **not** `pip install apache-airflow` into the app `.venv` for normal development.
- App tests: `pytest -q` without starting this compose.
- Do **not** merge C12 feature backfill into this DAG.
