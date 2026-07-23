# =============================================================================
# Warungio Marketplace — Dockerfile (OPTIMIZED untuk VPS 1GB RAM)
# Multi-stage build: base → dependencies → build-static → runtime
# - BuildKit cache mount untuk pip (build lebih cepat)
# - Build-static stage: collectstatic DIJALANKAN SAAT BUILD
#   → staticfiles fresh dari sumber, bukan copian dari host
# - Selective COPY ke runtime (assets/ 60MB tidak ikut ke image final)
# - --no-compile (image lebih kecil, ~20% hemat space)
# - Target: Ubuntu VPS 1GB RAM + Docker Compose + Cloud Run
# =============================================================================

# ---- Base Stage (build deps + pip packages) ----
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install build dependencies (compiler, MariaDB headers) — HANYA di stage ini
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

# =============================================================================
# NOTE: Stage ini menggunakan BuildKit cache mount (--mount=type=cache).
# Docker 20.10+ mengaktifkan BuildKit secara default.
# Jika menggunakan Docker < 20.10, set DOCKER_BUILDKIT=1:
#   export DOCKER_BUILDKIT=1 && docker-compose build
# Atau di docker-compose.yml:
#   build:
#     context: .
#     dockerfile: Dockerfile
#     args:
#       DOCKER_BUILDKIT: 1
# =============================================================================

# ---- Dependencies Stage (pip install dengan cache mount) ----
FROM base AS deps

# Cache pip downloads — BuildKit akan menyimpan cache di host,
# sehingga rebuild tidak perlu download ulang packages yang sama.
#
# NOTE: daphne, channels-redis, django-redis, hiredis SUDAH ada di requirements.txt.
# Tidak perlu install ulang di sini. Hanya uvicorn yang perlu ditambahkan
# karena entrypoint menggunakan gunicorn+uvicorn (bukan daphne).
COPY django_backend/requirements.txt /app/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel && \
    pip install --no-compile -r /app/requirements.txt && \
    pip install --no-compile uvicorn[standard]

# =============================================================================
# ---- Build Stage: collectstatic dijalankan SAAT BUILD (bukan saat startup) ----
# =============================================================================
# Alasan:
#   - staticfiles di-generate FRESH dari source, tidak dicopy dari host
#   - assets/ (60MB — audio, images) hanya ada di stage ini
#   - Final runtime stage hanya mendapat staticfiles/ hasil collectstatic
#   - Container startup jadi lebih cepat (skip collectstatic)
# =============================================================================
FROM deps AS build-static

# Salin semua direktori sumber static
# assets/ dan shared/ dirujuk oleh STATICFILES_DIRS di settings.py
COPY django_backend/ /app/django_backend/
COPY assets/ /app/assets/
COPY shared/ /app/shared/

ENV PYTHONPATH=/app/django_backend \
    DJANGO_SETTINGS_MODULE=config.settings

# =============================================================================
# 🔴 ROOT CAUSE FIX #1: DJANGO_SECRET_KEY Tidak Terpropagasi ke collectstatic
#
# Masalah:
#   RUN ... DJANGO_SECRET_KEY=${BUILD_SECRET_KEY} test -f ... && \
#              python manage.py collectstatic ...
#   Di bash, `VAR=val cmd1 && cmd2` hanya set VAR untuk cmd1 (test -f),
#   BUKAN untuk cmd2 (collectstatic). Settings.py kemudian raise
#   ImproperlyConfigured karena DJANGO_SECRET_KEY=None dan DEBUG=False.
#
# Fix:
#   Gunakan `export DJANGO_SECRET_KEY=${BUILD_SECRET_KEY}` sebagai
#   perintah terpisah, sehingga key persist untuk seluruh chain.
# Buat direktori logs (dibutuhkan settings.py saat import)
# Gunakan dummy key hanya untuk build (tidak bocor ke runtime)
# CELERY_ENABLED tidak perlu di-set karena config/__init__.py sekarang
# default ke 'false' (secure-by-default).
ARG BUILD_SECRET_KEY=django-insecure-build-only-key
RUN export DJANGO_SECRET_KEY=${BUILD_SECRET_KEY} && \
    mkdir -p /app/logs && \
    cd /app/django_backend && \
    # ── CRITICAL: Verify ALL source static files exist BEFORE collectstatic ──
    # Without this check, a .dockerignore regression that excludes
    # django_backend/static/ would silently produce 0 project files.
    test -f /app/django_backend/static/css/premium.css && \
    test -f /app/django_backend/static/css/landing.css && \
    test -f /app/django_backend/static/css/tokens.css && \
    test -f /app/django_backend/static/css/components.css && \
    test -f /app/django_backend/static/js/utils/auth-ui.js && \
    echo "=== Source: ALL 5 critical static files confirmed ===" && \
    python manage.py collectstatic --noinput 2>&1 && \
    # ── Verify ALL critical files were actually collected into the output ──
    test -f /app/staticfiles/css/premium.css && \
    test -f /app/staticfiles/css/landing.css && \
    test -f /app/staticfiles/css/tokens.css && \
    test -f /app/staticfiles/css/components.css && \
    test -f /app/staticfiles/js/utils/auth-ui.js && \
    echo "=== Collectstatic: ALL 5 critical files in output ===" && \
    COLLECTED_COUNT=$(find /app/staticfiles -type f 2>/dev/null | wc -l) && \
    echo "=== Total: $COLLECTED_COUNT static files collected ===" && \
    if [ "$COLLECTED_COUNT" -lt 50 ]; then \
        echo "ERROR: Only $COLLECTED_COUNT files collected (expected 50+)." >&2; \
        exit 1; \
    fi

# =============================================================================
# ---- Runtime Stage (CLEAN — build-essential, pkg-config, assets TIDAK ADA) ----
# =============================================================================
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install ONLY runtime libraries — minimal dan spesifik
# redis-tools: ~1MB, dibutuhkan oleh Redis heartbeat healthcheck
# untuk celery worker dan celery beat containers.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmariadb-dev-compat \
    ca-certificates \
    curl \
    mariadb-client \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages dari stage deps (tanpa .pyc — sudah --no-compile)
COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# ── Selective COPY dari build-static ──────────────────────────────────────
#   django_backend/  → kode Django (fresh dari source)
#   staticfiles/     → hasil collectstatic (fresh, dari build)
#   docker-entrypoint.sh  → entrypoint script
#   
#   assets/ (60MB)   → TIDAK DIKOPI — hanya ada di stage build-static
#   shared/ (12KB)   → TIDAK DIKOPI — hanya dibutuhkan collectstatic
#
# ── Template dirs: langsung dari build context (bukan dari build-static) ─
#   home/   → TEMPLATES.DIRS: BASE_DIR / 'home' (TemplateView di urls.py)
#   seller/ → TEMPLATES.DIRS: BASE_DIR / 'seller' (TemplateView di urls.py)
#   auth/   → TEMPLATES.DIRS: BASE_DIR / 'auth' (TemplateView di urls.py)
#   buyer/  → TEMPLATES.DIRS: BASE_DIR / 'buyer' (TemplateView di urls.py)
#
# Ini adalah partial HTML files (SPA shell), bukan Django templates .html.
# Django's filesystem.Loader akan mencari di sini saat render template.
# Tanpa direktori ini, semua halaman buyer/auth/seller return 404.
#
# Bandingkan dengan COPY . /app/: menghemat ~90% ruang image.
COPY --from=build-static /app/django_backend/ /app/django_backend/
COPY --from=build-static /app/staticfiles/ /app/staticfiles/
COPY home/ /app/home/
COPY seller/ /app/seller/
COPY auth/ /app/auth/
COPY buyer/ /app/buyer/
COPY docker-entrypoint.sh /app/docker-entrypoint.sh

ENV PYTHONPATH=/app/django_backend

# Buat direktori yang diperlukan, set entrypoint permission
# Gunakan sed instead of dos2unix untuk menghindari instalasi package tambahan
RUN mkdir -p /app/logs /app/django_backend/media && \
    sed -i 's/\r$//' /app/docker-entrypoint.sh && \
    chmod +x /app/docker-entrypoint.sh

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=5 \
    CMD curl -sf http://localhost:8000/health/ || exit 1

ENTRYPOINT ["/bin/bash", "/app/docker-entrypoint.sh"]
