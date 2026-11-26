"""Airflow DAG `spotify_weekly` — SPEC v2 Option B.

Q7 stage 1: ``schedule=None`` (manual-only until Phase 4 all-green).
Phase 3: ``bronze`` calls ``run_bronze``. ``build_silver`` / ``build_gold``
are still EmptyOperator placeholders (Phase 4).

Q8a OPEN: pass ``chart_date`` via DAG run conf/params — do not invent weekday.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from airflow import DAG  # pyright: ignore[reportMissingImports]
from airflow.operators.empty import EmptyOperator  # pyright: ignore[reportMissingImports]
from airflow.operators.python import PythonOperator  # pyright: ignore[reportMissingImports]

log = logging.getLogger(__name__)


def _run_bronze_task(**context: Any) -> None:
    # Lazy import: DAG file must parse even if the app package is missing.
    from spotify_pipeline.pipeline.run import run_bronze
    from spotify_pipeline.state.watermark import Watermark

    params = context["params"]
    watermark = Watermark.parse(
        params["chart_date"], params["chart_type"], params["country"]
    )
    log.info("bronze watermark=%s", watermark.as_tuple())

    # write_fs=False: Postgres music.raw_* is the SoR; container FS is ephemeral.
    summary = run_bronze(watermark, write_fs=False)
    log.info("bronze done summary=%s", summary)


with DAG(
    dag_id="spotify_weekly",
    description="Weekly Charts → Bronze → Silver → Gold (Option B)",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
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
    build_silver = EmptyOperator(task_id="build_silver")
    build_gold = EmptyOperator(task_id="build_gold")

    bronze >> build_silver >> build_gold
