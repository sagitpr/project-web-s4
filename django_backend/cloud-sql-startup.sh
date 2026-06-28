#!/bin/bash
# =============================================================================
# Warungio — Cloud Run Startup Script
# =============================================================================
# This script runs database migrations, collects static files,
# then starts Daphne with the proper PORT environment variable.
#
# Cloud SQL connection is configured via settings.py:
#   DB_HOST_TYPE=cloud_sql
#   CLOUD_SQL_INSTANCE=project:region:instance
#
# The Cloud SQL Auth Proxy (or Cloud SQL Python Connector) provides
# a Unix socket at /cloudsql/PROJECT:REGION:INSTANCE
# =============================================================================

set -e

echo "=== Warungio Cloud Run Startup ==="
echo "PORT: ${PORT:-8080}"
echo "USE_MYSQL: ${USE_MYSQL:-False}"
echo "DB_HOST_TYPE: ${DB_HOST_TYPE:-tcp}"
echo "DJANGO_DEBUG: ${DJANGO_DEBUG:-False}"
echo ""

# ── Wait for database if using TCP (docker-compose) ──
if [ "$DB_HOST_TYPE" = "tcp" ] && [ -n "$DB_HOST" ]; then
    echo "Waiting for database at $DB_HOST:${DB_PORT:-3306}..."
    for i in $(seq 1 30); do
        if python -c "import socket;s=socket.socket();s.settimeout(2);s.connect(('$DB_HOST',${DB_PORT:-3306}));s.close()" 2>/dev/null; then
            echo "Database is ready!"
            break
        fi
        echo "  Attempt $i/30 — waiting..."
        sleep 2
    done
fi

# ── Run database migrations ──
echo ""
echo "Running database migrations..."
python manage.py migrate --noinput
echo "Migrations complete."

# ── Collect static files ──
echo ""
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear
echo "Static files collected."

# ── Start Daphne ASGI server ──
echo ""
echo "Starting Daphne on 0.0.0.0:${PORT:-8080}..."
exec daphne -b 0.0.0.0 -p "${PORT:-8080}" config.asgi:application
