# =============================================================================
# Warungio Marketplace — Dockerfile
# Multi-stage build: base → dependencies → runtime
# =============================================================================

# ---- Base Stage ----
FROM python:3.14-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libmariadb-dev-compat \
    libmariadb-dev \
    pkg-config \
    gettext \
    && rm -rf /var/lib/apt/lists/*

# ---- Dependencies Stage ----
FROM base AS deps

COPY django_backend/requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install gunicorn daphne

# ---- Runtime Stage ----
FROM base AS runtime

COPY --from=deps /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

COPY . .

# Critical: Set PYTHONPATH so Django can find the 'config' module (lives at /app/django_backend/config/)
ENV PYTHONPATH=/app/django_backend

# Create static/media directories
RUN mkdir -p /app/staticfiles /app/django_backend/media /app/logs

RUN apt-get update && apt-get install -y dos2unix

RUN dos2unix /app/docker-entrypoint.sh
# Make entrypoint executable
RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 8080

# Use entrypoint script that runs migrations + collectstatic + starts Daphne
ENTRYPOINT ["/app/docker-entrypoint.sh"]
