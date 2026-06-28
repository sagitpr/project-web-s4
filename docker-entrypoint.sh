#!/bin/bash
# =============================================================================
# Warungio Marketplace — Docker Entrypoint
# Runs migrations (with retry), collects static files, then starts Daphne ASGI.
# Compatible with: local dev, Docker Compose, and Cloud Run.
# =============================================================================

set -o pipefail

cd /app/django_backend

echo "================================================"
echo "  Warungio Marketplace - Starting..."
echo "================================================"

# ------------------------------------------------------------------
# Health check: wait for database if USE_MYSQL is true
# ------------------------------------------------------------------
MAX_RETRIES=${DB_RETRIES:-30}
RETRY_DELAY=${DB_RETRY_DELAY:-2}

if [ "${USE_MYSQL,,}" = "true" ] || [ "${USE_MYSQL}" = "1" ]; then
    echo "[0/3] Waiting for database connection..."

    # Determine DB_HOST and DB_PORT — with safe defaults
    DB_HOST="${DB_HOST:-127.0.0.1}"
    DB_PORT="${DB_PORT:-3306}"

    retries=0
    while [ $retries -lt $MAX_RETRIES ]; do
        # Use python to check DB connectivity (works whether TCP or Cloud SQL socket)
        if python -c "
import os
import sys

db_host_type = os.environ.get('DB_HOST_TYPE', 'tcp').lower()

if db_host_type == 'cloud_sql':
    socket_path = os.environ.get('CLOUD_SQL_SOCKET', '/cloudsql/' + os.environ.get('CLOUD_SQL_INSTANCE', ''))
    if os.path.exists(socket_path):
        sys.exit(0)
    else:
        sys.exit(1)
else:
    import socket
    host = os.environ.get('DB_HOST', '127.0.0.1')
    port = int(os.environ.get('DB_PORT', '3306'))
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    try:
        s.connect((host, port))
        s.close()
        sys.exit(0)
    except:
        sys.exit(1)
" 2>/dev/null; then
            echo "  -> Database is ready."
            break
        else
            retries=$((retries + 1))
            echo "  -> Waiting for database... (${retries}/${MAX_RETRIES})"
            sleep $RETRY_DELAY
        fi
    done

    if [ $retries -ge $MAX_RETRIES ]; then
        echo "  *********************************************************************"
        echo "  WARNING: Database not available after ${MAX_RETRIES} retries."
        echo "  Continuing without migrations — app may have limited functionality."
        echo "  If using Cloud SQL, ensure the instance is running and connected."
        echo "  Set DB_RETRIES=60 or higher for slow-starting databases."
        echo "  *********************************************************************"
        SKIP_MIGRATIONS="true"
    fi
else
    echo "[0/3] Using SQLite — no database wait needed."
fi

# ------------------------------------------------------------------
# Collect static files
# ------------------------------------------------------------------
echo "[1/3] Collecting static files..."
python manage.py collectstatic --noinput
echo "  -> static files collected."

# ------------------------------------------------------------------
# Database migrations (skip if DB was not available)
# ------------------------------------------------------------------
if [ "${SKIP_MIGRATIONS,,}" != "true" ]; then
    echo "[2/3] Running database migrations..."
    if python manage.py migrate --noinput; then
        echo "  -> migrations complete."
    else
        echo "  -> WARNING: Migration failed. Continuing anyway."
        echo "     App will start but database may be out of date."
    fi
else
    echo "[2/3] Skipping migrations (database not available)."
fi

# ------------------------------------------------------------------
# Superuser creation (optional)
# ------------------------------------------------------------------
if [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "  -> Creating superuser..."
    echo "from accounts.models import User; User.objects.create_superuser('$DJANGO_SUPERUSER_EMAIL', '$DJANGO_SUPERUSER_PASSWORD')" | python manage.py shell 2>/dev/null || true
fi

# ------------------------------------------------------------------
# Start Celery worker in background (if REDIS_URL is set)
# ------------------------------------------------------------------
if [ -n "$REDIS_URL" ] && [ "${REDIS_URL}" != "redis://..." ] && [ "${REDIS_URL}" != "" ]; then
    echo "[3/3] Starting Celery worker..."
    cd /app/django_backend
    # Start Celery worker in background; logs to celery.log
    celery -A config worker --loglevel=INFO --concurrency=2 --detach --logfile=/app/logs/celery.log 2>/dev/null || true
    # Start Celery beat scheduler in background
    celery -A config beat --loglevel=INFO --detach --logfile=/app/logs/celery_beat.log 2>/dev/null || true
    echo "  -> Celery worker & beat started."
else
    echo "[3/3] REDIS_URL not set — skipping Celery."
fi

# ------------------------------------------------------------------
# Start server
# ------------------------------------------------------------------
PORT="${PORT:-8080}"

echo "================================================"
echo "  Warungio running on 0.0.0.0:${PORT}"
echo "================================================"

exec daphne -b 0.0.0.0 -p ${PORT} config.asgi:application
