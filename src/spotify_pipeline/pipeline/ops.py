"""SPEC v2 §19a addendum — best-effort Ops log in ``music.pipeline_runs``.

One row per Airflow ``dag_run`` keyed by ``(dag_id, dag_run_id)``. The DAG task
wrappers call ``record_*``; a failed write only logs a WARNING and never changes
the task result (Q1/Q6: Ops is not a gate). Simple SQL, no bind params (pooler-safe).
No Airflow import here (Q11) and not wired into ``run.py`` (ANTI-RUN).
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, is_dataclass
from typing import Any

from spotify_pipeline.db.postgres import connect_postgres
from spotify_pipeline.pipeline.bronze.writers import _sql_jsonb, _sql_str
from spotify_pipeline.state.watermark import Watermark

log = logging.getLogger(__name__)

_ERROR_LIMIT = 1000
_DB_URI = re.compile(r"postgres(?:ql)?://\S+", re.IGNORECASE)


def record_start(
    dag_id: str, dag_run_id: str, task: str, watermark: Watermark | None = None
) -> None:
    """Task attempt begins (also re-opens a failed/success row after Clear)."""
    _execute(_upsert_sql(dag_id, dag_run_id, "running", task, watermark))


def record_success(
    dag_id: str,
    dag_run_id: str,
    task: str,
    result: Any,
    *,
    final: bool = False,
    watermark: Watermark | None = None,
) -> None:
    """Task finished; ``final`` (build_gold) closes the run as success."""
    status = "success" if final else "running"
    _execute(_upsert_sql(dag_id, dag_run_id, status, task, watermark, result=result))


def record_failure(dag_id: str, dag_run_id: str, task: str, error: str) -> None:
    """Task failed after its last retry (task-level ``on_failure_callback``)."""
    _execute(_upsert_sql(dag_id, dag_run_id, "failed", task, error=error))


def clean_error(message: str, limit: int = _ERROR_LIMIT) -> str:
    """Redact DB URIs and truncate so error_message never carries secrets."""
    return _DB_URI.sub("<redacted-uri>", message)[:limit]


def _upsert_sql(
    dag_id: str,
    dag_run_id: str,
    status: str,
    task: str,
    watermark: Watermark | None = None,
    *,
    result: Any = None,
    error: str | None = None,
) -> str:
    date_sql, type_sql, country_sql = "NULL", "NULL", "NULL"
    if watermark is not None:
        date_sql = f"CAST({_sql_str(watermark.chart_date)} AS date)"
        type_sql = _sql_str(watermark.chart_type)
        country_sql = _sql_str(watermark.country)
    summary_sql = "'{}'::jsonb"
    if result is not None:
        summary_sql = f"jsonb_build_object({_sql_str(task)}, {_sql_jsonb(_jsonable(result))})"
    finished_sql = "NULL" if status == "running" else "now()"
    err_task = _sql_str(task) if status == "failed" else "NULL"
    err_msg = "NULL" if error is None else _sql_str(clean_error(error))
    return f"""
        INSERT INTO music.pipeline_runs
            (dag_id, dag_run_id, chart_date, chart_type, country, status,
             current_task, finished_at, error_task, error_message, summary)
        VALUES
            ({_sql_str(dag_id)}, {_sql_str(dag_run_id)}, {date_sql}, {type_sql},
             {country_sql}, {_sql_str(status)}, {_sql_str(task)}, {finished_sql},
             {err_task}, {err_msg}, {summary_sql})
        ON CONFLICT (dag_id, dag_run_id) DO UPDATE SET
            status = EXCLUDED.status,
            current_task = EXCLUDED.current_task,
            finished_at = EXCLUDED.finished_at,
            error_task = EXCLUDED.error_task,
            error_message = EXCLUDED.error_message,
            chart_date = COALESCE(EXCLUDED.chart_date, music.pipeline_runs.chart_date),
            chart_type = COALESCE(EXCLUDED.chart_type, music.pipeline_runs.chart_type),
            country = COALESCE(EXCLUDED.country, music.pipeline_runs.country),
            summary = music.pipeline_runs.summary || EXCLUDED.summary,
            updated_at = now()
        """


def _jsonable(obj: Any) -> dict[str, Any]:
    """Dataclass / dict result -> plain JSON dict (dates etc. stringified)."""
    data = asdict(obj) if is_dataclass(obj) and not isinstance(obj, type) else obj
    return json.loads(json.dumps(data, default=str))


def _execute(sql: str) -> None:
    # ponytail: one short connection per write (<=7 per weekly run); no connect
    # timeout (shared connect_postgres has none). Add one if a blackholed DB bites.
    try:
        conn = connect_postgres()
        try:
            conn.run(sql)
        finally:
            conn.close()
    except Exception as exc:  # noqa: BLE001 — best-effort by design
        log.warning("ops pipeline_runs write skipped: %s", clean_error(f"{type(exc).__name__}: {exc}"))
