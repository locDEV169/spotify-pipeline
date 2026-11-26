FROM apache/airflow:2.9.3-python3.12

# Install only the app package (deps come from pyproject.toml).
# Use Airflow's own constraints so app deps cannot upgrade packages Airflow pins.
# Airflow itself stays out of the app pyproject (Q11=A / ANTI-DEPS).
#
# Editable install + docs/sql: silver/gold resolve SQL templates as
# <repo root>/docs/sql/... via Path(__file__).parents[4], so the image must
# keep the repo layout (/opt/spotify-pipeline/{src,docs/sql}).
# Rebuild after changing src/ or docs/sql/:
#   docker build -f docker/airflow/Dockerfile -t spotify-pipeline-airflow:local .
COPY --chown=airflow:root pyproject.toml README.md /opt/spotify-pipeline/
COPY --chown=airflow:root src /opt/spotify-pipeline/src
COPY --chown=airflow:root docs/sql /opt/spotify-pipeline/docs/sql
RUN pip install --no-cache-dir \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.9.3/constraints-3.12.txt" \
    -e /opt/spotify-pipeline
