#!/bin/bash
# =============================================================================
# Warungio Marketplace — Docker Entrypoint (SPLIT BY CONTAINER ROLE)
#
# BEHAVIOR:
#   No args ($# -eq 0)  → DJANGO mode: wait DB → collectstatic → sync_migrations
#                          → migrate → superuser → gunicorn+uvicorn (foreground)
#   With args ($# -gt 0) → CELERY/BEAT mode: wait DB → exec "$@" (skip startup)
#
# NOTE: collectstatic dijalankan SETIAP startup karena Docker named volume
#       (static_volume) persist meskipun image di-rebuild. Tanpa ini,
#       perubahan CSS/JS tidak akan muncul di volume yang sudah ada.
#       Durasi: ~1-2 detik untuk ~6 file (negligible).
#
# Docker Compose passes `command:` as args to the entrypoint, so:
#   django: no command            → full startup + gunicorn+uvicorn
#   celery: command: [celery ...] → wait DB + celery worker
#   beat:   command: [celery ...] → wait DB + celery beat
# =============================================================================

set -o pipefail
set -e

cd /app/django_backend

echo "================================================"
echo "  Warungio Marketplace - Starting..."
echo "================================================"

# ─── Configuration ──────────────────────────────────────────────────────────
MAX_RETRIES=${DB_RETRIES:-60}
RETRY_DELAY=${DB_RETRY_DELAY:-2}
PORT="${PORT:-8000}"

# ------------------------------------------------------------------
# WAIT FOR DATABASE — needed by ALL container types
# ------------------------------------------------------------------
if [ "${USE_MYSQL}" = "true" ] || [ "${USE_MYSQL}" = "1" ]; then
    echo "[WAIT] Waiting for MariaDB (real auth check)..."

    db_host="${DB_HOST:-127.0.0.1}"
    db_port="${DB_PORT:-3306}"
    db_user="${DB_USER:-warungio}"
    db_pass="${DB_PASS:?FATAL: DB_PASS is not set. Create a .env file with DB_PASS=your_secure_password}"
    db_retries=0

    while [ ${db_retries} -lt ${MAX_RETRIES} ]; do
        if mysqladmin ping \
            -h "${db_host}" \
            -P "${db_port}" \
            -u "${db_user}" \
            -p"${db_pass}" \
            --skip-ssl \
            --silent 2>/dev/null; then
            echo "  -> MariaDB is ready (authenticated successfully)."
            break
        fi

        db_retries=$((db_retries + 1))
        echo "  -> Waiting for MariaDB... (${db_retries}/${MAX_RETRIES})"
        sleep ${RETRY_DELAY}
    done

    if [ ${db_retries} -ge ${MAX_RETRIES} ]; then
        echo "  ERROR: MariaDB not reachable or authentication failed after ${MAX_RETRIES} retries."
        echo "  Check DB_HOST, DB_PORT, DB_USER, DB_PASS in your .env configuration."
        echo "  Ensure the mysql service is healthy: docker-compose ps mysql"
        exit 1
    fi
else
    echo "[WAIT] Using SQLite — no database wait needed."
fi


# ------------------------------------------------------------------
# CELERY / BEAT MODE  — skip startup tasks, run the passed command
# ------------------------------------------------------------------
# docker-compose passes `command:` as $@ to the entrypoint.
# celery service:    command: ["celery", "-A", "config", "worker", ...]
# beat service:      command: ["celery", "-A", "config", "beat", ...]
if [ $# -gt 0 ]; then
    echo "[MODE] Container role detected from command arguments."
    echo "  -> Skipping migrations and superuser (not needed for workers)."
    echo "  -> Starting: $@"
    exec "$@"
fi


# ══════════════════════════════════════════════════════════════════════════════
# DJANGO MODE — Full startup (migrations + superuser + gunicorn)
# ══════════════════════════════════════════════════════════════════════════════
# NOTE: collectstatic dijalankan SETIAP startup untuk memastikan Docker named
#       volume (static_volume) selalu sync dengan source code terbaru.
#       Named volume persist meskipun image di-rebuild, jadi tanpanya
#       perubahan CSS/JS tidak akan muncul sampai volume dihapus manual.
#       Biaya: ~1-2 detik untuk ~6 file (negligible).
#
# NOTE: ASGI server menggunakan Gunicorn + UvicornWorker.
#       BUKAN Daphne. Daphne di-replace karena Gunicorn memberikan
#       worker lifecycle management (max_requests) yang mencegah
#       memory leak tanpa perlu container restart.
# ══════════════════════════════════════════════════════════════════════════════
echo "[MODE] Django web container — running full startup."

# ------------------------------------------------------------------
# STEP 0: Collect static files (sync volume with latest source)
# ------------------------------------------------------------------
# Pre-flight check: Ensure DJANGO_SECRET_KEY is available.
# Without this, settings.py raises ImproperlyConfigured at import time.
# config/__init__.py now defaults CELERY_ENABLED to 'false' (secure-by-default),
# so Celery circular import during collectstatic is no longer a concern.
echo "[0/3] Collecting static files..."
if [ -z "${DJANGO_SECRET_KEY}" ]; then
    if [ "${DJANGO_DEBUG}" = "true" ] || [ "${DJANGO_DEBUG}" = "1" ]; then
        echo "  -> WARNING: DJANGO_SECRET_KEY not set. Using dev fallback."
        export DJANGO_SECRET_KEY="django-insecure-dev-only-key-do-not-use-in-production"
    else
        echo "  -> ERROR: DJANGO_SECRET_KEY is not set and DEBUG=false. Aborting."
        echo "  -> Set DJANGO_SECRET_KEY in your .env file or environment."
        exit 1
    fi
fi
python manage.py collectstatic --noinput \
    && echo "  -> Static files collected." \
    || echo "  -> WARNING: collectstatic startup sync failed. Check Docker build output for static file validation errors."

# ------------------------------------------------------------------
# STEP 1: Sync migrations (non-fatal — gunicorn tetap jalan walau gagal)
# ------------------------------------------------------------------
echo "[1/3] Syncing migrations with existing database..."
python manage.py sync_migrations --no-backup \
    && echo "  -> Migration sync complete." \
    || echo "  -> WARNING: sync_migrations gagal (non-fatal). Lanjut startup..."

# ------------------------------------------------------------------
# STEP 2: Run database migrations (safety net for any remaining)
# ------------------------------------------------------------------
echo "[2/3] Applying any remaining migrations..."
python manage.py migrate --noinput \
    && echo "  -> Migration apply complete." \
    || echo "  -> WARNING: migrate gagal (non-fatal). Lanjut startup..."
echo "  -> Migrations step selesai (server akan tetap jalan)."

# ------------------------------------------------------------------
# Superuser (optional, non-fatal)
# ------------------------------------------------------------------
if [ -n "${DJANGO_SUPERUSER_EMAIL}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD}" ]; then
    echo "  -> Creating superuser..."
    python manage.py shell -c "
import os
from accounts.models import User
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', '')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', '')
username = email.split('@')[0] if email else 'admin'
if email and password:
    if not User.objects.filter(email=email).exists():
        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
            full_name=username,
        )
        print('Superuser', email, 'created.')
    else:
        print('Superuser', email, 'already exists.')
" 2>/dev/null || echo "  -> WARNING: Superuser creation failed (non-fatal)."
fi

# ------------------------------------------------------------------
# START ASGI server (foreground — container stays alive)
# ------------------------------------------------------------------
# Uses Gunicorn with Uvicorn worker for better connection handling:
# - 1 worker (matches 1 vCPU — no benefit from more)
# - 2 threads per worker for concurrent I/O handling
# - 1000 max requests per worker before restart (prevents memory leaks)
# - 120s timeout (reduced from default to prevent connection pileup on 1GB VPS)
# - --worker-connections=256 ensures we don't exceed DB connection pool
# - --keep-alive=2 aggressively closes idle connections (free up memory)
#
# Note: Daphne-only mode was replaced by Gunicorn+Uvicorn because:
#   - Gunicorn provides worker lifecycle management (max_requests)
#   - Uvicorn provides async ASGI capability identical to Daphne
#   - Both support WebSocket via ASGI
#   - Gunicorn's --max-requests prevents memory leaks without container restart
#
echo "Starting Gunicorn+Uvicorn on 0.0.0.0:${PORT}..."
echo "================================================"
echo "  Warungio running on 0.0.0.0:${PORT}"
echo "================================================"

exec gunicorn config.asgi:application \
    -k uvicorn.workers.UvicornWorker \
    -w 1 \
    --threads 2 \
    --worker-connections 128 \
    --max-requests 500 \
    --max-requests-jitter 50 \
    --timeout 180 \
    --keep-alive 2 \
    --bind 0.0.0.0:${PORT} \
    --access-logfile '-' \
    --access-logformat '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"' \
    --error-logfile '-' \
    --log-level warning \
    --capture-output \
    --enable-stdio-inheritance
