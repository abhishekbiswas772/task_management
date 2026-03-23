# ─── Stage 1: build ───────────────────────────────────────────────────────────
# Install Python deps into an isolated venv so the runtime stage is lean.
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Build deps for asyncpg / psycopg C extensions
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       gcc \
       libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --upgrade pip wheel \
    && pip install -r requirements.txt


# ─── Stage 2: runtime ─────────────────────────────────────────────────────────
# Only copy the venv + app source; no build tools in the final image.
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=5000

WORKDIR /app

# postgresql-client → provides pg_dump for scheduled backups (lightweight)
# Create non-root user in the same layer to minimise image layers
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       postgresql-client \
       libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash --uid 1001 appuser

# Copy venv from builder
COPY --from=builder /opt/venv /opt/venv

# Copy only application source (no .venv, no *.db, no backups — see .dockerignore)
COPY --chown=appuser:appuser . .

# Runtime directories
RUN mkdir -p /app/flask_session /app/backups \
    && chown -R appuser:appuser /app/flask_session /app/backups

USER appuser

EXPOSE 5000

# Use python run.py so Flask's debug reloader works in dev;
# for production swap to: gunicorn -k gevent -w 2 -b 0.0.0.0:5000 "run:app"
CMD ["python", "run.py"]
