#!/bin/bash
# =============================================================================
# Warungio Marketplace — Docker Entrypoint (SPLIT BY CONTAINER ROLE)
#
# BEHAVIOR:
#   No args ($# -eq 0)  → DJANGO mode: wait DB → sync_migrations → migrate
#                          → superuser → daphne (foreground)
#   With args ($# -gt 0) → CELERY/BEAT mode: wait DB → exec "$@" (skip startup)
#
# NOTE: collectstatic sudah dijalankan saat Docker build (stage build-static),
# tidak perlu dijalankan ulang saat container start. Ini mempercepat startup
# dan memastikan staticfiles selalu fresh dari source.
#
# Docker Compose passes `command:` as args to the entrypoint, so:
#   django: no command            → full startup + daphne
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
# DJANGO MODE — Full startup (migrations + superuser + daphne)
# ══════════════════════════════════════════════════════════════════════════════
# NOTE: collectstatic TIDAK dijalankan di sini karena sudah dilakukan
#       saat Docker build di stage build-static. Ini mempercepat startup
#       container dan mengurangi I/O disk pada VPS 1GB RAM.
# ══════════════════════════════════════════════════════════════════════════════
echo "[MODE] Django web container — running full startup."

# ------------------------------------------------------------------
# STEP 1: Sync migrations
# ------------------------------------------------------------------
echo "[1/2] Syncing migrations with existing database..."
python manage.py sync_migrations --no-backup
echo "  -> Migration sync complete."

# ------------------------------------------------------------------
# STEP 2: Run database migrations (safety net for any remaining)
# ------------------------------------------------------------------
echo "[2/2] Applying any remaining migrations..."
python manage.py migrate --noinput
echo "  -> Migrations complete."

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
# START Daphne ASGI server (foreground — container stays alive)
# ------------------------------------------------------------------
echo "Starting Daphne on 0.0.0.0:${PORT}..."
echo "================================================"
echo "  Warungio running on 0.0.0.0:${PORT}"
echo "================================================"

exec daphne -b 0.0.0.0 -p ${PORT} config.asgi:application
