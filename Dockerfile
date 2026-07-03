# =============================================================================
# Warungio Marketplace — Dockerfile
# Multi-stage build: base → dependencies → runtime
# Target: Ubuntu VPS + Docker Compose + Cloud Run
# =============================================================================

# ---- Base Stage (build deps + pip packages) ----
FROM python:3.12-slim AS base

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
    ca-certificates \
    curl \
    mariadb-client \
    && rm -rf /var/lib/apt/lists/*

# ---- Dependencies Stage ----
FROM base AS deps

COPY django_backend/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r /app/requirements.txt && \
    pip install daphne channels-redis

# ---- Runtime Stage (CLEAN — no build-essential, no pkg-config) ----
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install ONLY runtime libraries — no build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmariadb-dev-compat \
    ca-certificates \
    curl \
    mariadb-client \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

COPY . /app/

ENV PYTHONPATH=/app/django_backend

RUN mkdir -p /app/staticfiles /app/django_backend/media /app/logs && \
    dos2unix /app/docker-entrypoint.sh && \
    chmod +x /app/docker-entrypoint.sh && \
    apt-get purge -y dos2unix && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD python -c "import os, urllib.request; req = urllib.request.Request(f'http://localhost:{os.getenv(\"PORT\",\"8000\")}/health/'); req.add_header('X-Forwarded-Proto', 'https'); urllib.request.urlopen(req)"

ENTRYPOINT ["/bin/bash", "/app/docker-entrypoint.sh"]
