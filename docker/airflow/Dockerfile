FROM apache/airflow:2.9.3-python3.12

# Install only the app package (deps come from pyproject.toml).
# Use Airflow's own constraints so app deps cannot upgrade packages Airflow pins.
# Airflow itself stays out of the app pyproject (Q11=A / ANTI-DEPS).
# Rebuild after changing src/: docker compose -f docker/airflow/docker-compose.yml build
COPY --chown=airflow:root pyproject.toml README.md /opt/spotify-pipeline/
COPY --chown=airflow:root src /opt/spotify-pipeline/src
RUN pip install --no-cache-dir \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.9.3/constraints-3.12.txt" \
    /opt/spotify-pipeline
