# Celery — Aktif untuk async task processing.
# Celery worker dan beat berjalan di container terpisah (docker-compose).
# Nonaktifkan sementara dengan set CELERY_ENABLED=false di .env.

import os

CELERY_ENABLED = os.environ.get('CELERY_ENABLED', 'true').lower() in ('true', '1', 'yes')

if CELERY_ENABLED:
    from .celery import app as celery_app  # noqa: F401
    __all__ = ('celery_app',)
