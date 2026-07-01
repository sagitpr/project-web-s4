#!/bin/bash
# =============================================================================
# Warungio Marketplace — Docker Entrypoint (SINGLE STARTUP FLOW)
#
# THIS IS THE SINGLE ENTRYPOINT. No CMD or command: override in docker-compose.
# Order: 1) Wait for DB (real auth check)  2) Collect static files
#        3) Migrate (fail if fails)        4) Superuser (optional)
#        5) Celery (background)            6) Daphne (foreground)
# =============================================================================

set -o pipefail
set -e  # Exit immediately on any unhandled error

cd /app/django_backend

echo "================================================"
echo "  Warungio Marketplace - Starting..."
echo "================================================"

# ─── Configuration ──────────────────────────────────────────────────────────
MAX_RETRIES=${DB_RETRIES:-60}
RETRY_DELAY=${DB_RETRY_DELAY:-2}
PORT="${PORT:-8000}"

# ------------------------------------------------------------------
# STEP 0: Wait for MariaDB with REAL AUTHENTICATION CHECK
# ------------------------------------------------------------------
if [ "${USE_MYSQL}" = "true" ] || [ "${USE_MYSQL}" = "1" ]; then
    echo "[1/5] Waiting for MariaDB (real auth check)..."

    db_host="${DB_HOST:-127.0.0.1}"
    db_port="${DB_PORT:-3306}"
    db_user="${DB_USER:-warungio}"
    db_pass="${DB_PASS:?FATAL: DB_PASS is not set. Create a .env file with DB_PASS=your_secure_password}"
    db_retries=0

    while [ ${db_retries} -lt ${MAX_RETRIES} ]; do
        # Use mysqladmin with actual credentials for a real auth check
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
    echo "[1/5] Using SQLite — no database wait needed."
fi

# ------------------------------------------------------------------
# STEP 1: Collect static files (non-fatal on warnings)
# ------------------------------------------------------------------
echo "[2/5] Collecting static files..."
set +e
python manage.py collectstatic --noinput 2>&1
COLLECTSTATUS=$?
set -e
if [ ${COLLECTSTATUS} -ne 0 ]; then
    echo "  -> WARNING: collectstatic encountered issues (non-fatal, continuing)."
else
    echo "  -> Static files collected."
fi

# ------------------------------------------------------------------
# STEP 2: Run database migrations (single migrate command)
# ------------------------------------------------------------------
echo "[3/5] Running database migrations..."
python manage.py migrate --noinput
echo "  -> Migrations complete."

# ------------------------------------------------------------------
# STEP 3: Create superuser (optional, non-fatal)
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
# STEP 4: Start Celery worker + beat (background, only if Redis configured)
# ------------------------------------------------------------------
# Kill any stale Celery beat PID files before starting
rm -f /app/logs/celerybeat.pid /app/logs/celerybeat-schedule.db 2>/dev/null || true

# Only start Celery if REDIS_URL is configured to a non-localhost remote
REDIS_CHECK=$(python3 -c "
import os
url = os.environ.get('REDIS_URL', '')
if url and not url.startswith('redis://localhost') and not url.startswith('redis://127.0.0.1'):
    print('ready')
else:
    print('skip')
" 2>/dev/null || echo "skip")

if [ "${REDIS_CHECK}" = "ready" ]; then
    echo "[4/5] Starting Celery worker..."
    mkdir -p /app/logs
    # Start Celery worker in background; log failure but don't block Daphne
    celery -A config worker --loglevel=INFO --concurrency=2 \
        --detach --logfile=/app/logs/celery.log 2>&1 || \
        echo "  -> WARNING: Celery worker failed to start. Check /app/logs/celery.log"
    celery -A config beat --loglevel=INFO \
        --detach --logfile=/app/logs/celery_beat.log 2>&1 || \
        echo "  -> WARNING: Celery beat failed to start. Check /app/logs/celery_beat.log"
    echo "  -> Celery worker & beat started."
else
    echo "[4/5] Redis not configured — skipping Celery."
fi

# ------------------------------------------------------------------
# START Daphne ASGI server (foreground — container stays alive)
# ------------------------------------------------------------------
echo "[5/5] Starting Daphne on 0.0.0.0:${PORT}..."
echo "================================================"
echo "  Warungio running on 0.0.0.0:${PORT}"
echo "================================================"

exec daphne -b 0.0.0.0 -p ${PORT} config.asgi:application
