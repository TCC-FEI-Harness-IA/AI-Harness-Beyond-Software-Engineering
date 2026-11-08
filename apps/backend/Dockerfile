# syntax=docker/dockerfile:1

# ─── base ───────────────────────────────────────────────────────────────────
# Camada comum a dev e prod: dependências de runtime instaladas uma única vez.
# Quando o backend ganhar um banco (Postgres, etc.), o client/driver Python entra
# aqui (requirements.txt) e, se precisar de lib nativa (ex.: libpq para psycopg),
# o `apt-get install` correspondente entra neste estágio, antes do `pip install`.
FROM python:3.12-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# ─── dev ────────────────────────────────────────────────────────────────────
# Código entra via bind mount (docker-compose.dev.yml); a imagem só precisa das
# ferramentas de desenvolvimento. Reload automático a cada alteração de arquivo.
FROM base AS dev

COPY requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ─── prod ───────────────────────────────────────────────────────────────────
# Imagem final enxuta: só o runtime e o código da aplicação, sem ferramentas de dev.
FROM base AS prod

COPY src ./src

RUN useradd --create-home --shell /bin/bash appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
