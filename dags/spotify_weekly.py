"""Airflow DAG `spotify_weekly` — SPEC v2 Option B.

Chain: ``bronze`` (run_bronze) >> ``build_silver`` >> ``build_gold``.
Each task calls one library entrypoint for the same watermark; default trigger
semantics (no soft-fail) — a failed upstream stops downstream. Silver/Gold are DB-only.

Q7 stage 2: weekly schedule Mon 09:00 ``Asia/Bangkok`` (``catchup=False``,
``max_active_runs=1``). Q8a (locked): a scheduled run derives ``chart_date`` =
most recent Thursday before ``data_interval_end``. Manual runs pass
``chart_date`` via conf/params; an explicit value always wins.
History is not back-filled: Charts ``public/v0`` only serves the live week, so
weeks accumulate one scheduled run at a time.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import pendulum  # pyright: ignore[reportMissingImports]
from airflow import DAG  # pyright: ignore[reportMissingImports]
from airflow.operators.python import PythonOperator  # pyright: ignore[reportMissingImports]

log = logging.getLogger(__name__)


def _watermark(context: dict[str, Any]):
    # Lazy import: DAG file must parse even if the app package is missing.
    from spotify_pipeline.state.watermark import Watermark, chart_date_before

    params = context["params"]
    chart_date = params["chart_date"]
    if not chart_date and context["dag_run"].run_type == "scheduled":
        run_end = context["data_interval_end"].in_timezone(context["dag"].timezone)
        chart_date = chart_date_before(run_end.date())
    return Watermark.parse(chart_date, params["chart_type"], params["country"])


def _run_bronze_task(**context: Any) -> None:
    from spotify_pipeline.pipeline.run import run_bronze

    watermark = _watermark(context)
    log.info("bronze watermark=%s", watermark.as_tuple())

    # write_fs=False: Postgres music.raw_* is the SoR; container FS is ephemeral.
    summary = run_bronze(watermark, write_fs=False)
    log.info("bronze done summary=%s", summary)


def _build_silver_task(**context: Any) -> None:
    from spotify_pipeline.pipeline.silver import build_silver

    watermark = _watermark(context)
    log.info("build_silver watermark=%s", watermark.as_tuple())
    result = build_silver(watermark)
    log.info("build_silver done result=%s", result)


def _build_gold_task(**context: Any) -> None:
    from spotify_pipeline.pipeline.gold import build_gold

    watermark = _watermark(context)
    log.info("build_gold watermark=%s", watermark.as_tuple())
    result = build_gold(watermark)
    log.info("build_gold done result=%s", result)


with DAG(
    dag_id="spotify_weekly",
    description="Weekly Charts → Bronze → Silver → Gold (Option B)",
    # start_date = a Monday just before the first run: the first interval ends
    # Mon 2026-11-30 09:00, and catchup=False never back-fills older intervals.
    start_date=pendulum.datetime(2026, 11, 23, tz="Asia/Bangkok"),
    schedule="0 9 * * 1",
    catchup=False,
    max_active_runs=1,  # serial runs: no overlapping API/DB load (P5-08)
    tags=["spotify", "medallion", "option-b"],
    params={
        "chart_date": "",
        "chart_type": "weekly_top_songs",
        "country": "global",
    },
) as dag:
    bronze = PythonOperator(
        task_id="bronze",
        python_callable=_run_bronze_task,
        retries=1,
        retry_delay=timedelta(minutes=5),
    )
    # ponytail: Silver/Gold are DB-only + idempotent upserts; 1 short retry covers
    # transient DB errors. Revisit if OQ-1 (retry policy) is decided differently.
    build_silver = PythonOperator(
        task_id="build_silver",
        python_callable=_build_silver_task,
        retries=1,
        retry_delay=timedelta(minutes=1),
    )
    build_gold = PythonOperator(
        task_id="build_gold",
        python_callable=_build_gold_task,
        retries=1,
        retry_delay=timedelta(minutes=1),
    )

    bronze >> build_silver >> build_gold
