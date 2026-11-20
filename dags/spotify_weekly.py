"""Airflow DAG `spotify_weekly` — SPEC v2 Option B skeleton (Phase 2).

Q7 stage 1: ``schedule=None`` (manual-only until Phase 4 all-green).
Phase 2: EmptyOperator placeholders. Phase 3+ wires ``run_bronze`` /
``build_silver`` / ``build_gold``.

Q8a OPEN: pass ``chart_date`` via DAG run conf/params — do not invent weekday.
"""

from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.operators.empty import EmptyOperator

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
    bronze = EmptyOperator(task_id="bronze")
    build_silver = EmptyOperator(task_id="build_silver")
    build_gold = EmptyOperator(task_id="build_gold")

    bronze >> build_silver >> build_gold
