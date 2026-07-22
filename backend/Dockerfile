FROM python:3.11-slim
WORKDIR /app

# Capa de deps separada del código para cachear mejor entre builds.
COPY pyproject.toml ./
COPY cs2tracker ./cs2tracker
RUN pip install --no-cache-dir .

COPY alembic.ini ./
COPY alembic ./alembic

# Mismo Dockerfile para el servicio API y el worker de auto-fetch; el CMD
# real lo define cada servicio en docker-compose.yml (`cs2-api` vs
# `cs2-ingest --source steam`).
CMD ["cs2-api"]
