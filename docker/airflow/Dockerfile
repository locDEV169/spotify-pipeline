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
# flask is skipped: only src/spotify_pipeline/api needs it (>=3.1), the DAG does
# not, and Airflow 2.9.3's constraints pin flask==2.2.5 (resolver conflict).
RUN pip install --no-cache-dir --no-deps -e /opt/spotify-pipeline \
 && python -c "import tomllib; print('\n'.join(d for d in tomllib.load(open('/opt/spotify-pipeline/pyproject.toml','rb'))['project']['dependencies'] if not d.startswith('flask')))" > /tmp/app-requirements.txt \
 && pip install --no-cache-dir \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.9.3/constraints-3.12.txt" \
    -r /tmp/app-requirements.txt
