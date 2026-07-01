#!/bin/bash
# =============================================================================
# ⚠️  DEPRECATED — This script is superseded by docker-entrypoint.sh
#
# This file is kept for reference only. The Dockerfile ENTRYPOINT now uses
# docker-entrypoint.sh which handles: DB wait → collectstatic → migrate →
# Celery → Daphne for all environments (local dev, Docker Compose, Cloud Run).
#
# Original Cloud Run startup logic has been consolidated into
# docker-entrypoint.sh to avoid code duplication.
# =============================================================================

echo "=== Warungio Cloud Run Startup (DEPRECATED) ==="
echo "This script is deprecated. Use docker-entrypoint.sh instead."
echo "See: /app/docker-entrypoint.sh"
echo ""

set -e

cd /app/django_backend

exec daphne -b 0.0.0.0 -p "${PORT:-8080}" config.asgi:application
