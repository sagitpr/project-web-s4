# Celery — Aktif untuk async task processing.
# Celery worker dan beat berjalan di container terpisah (docker-compose).
#
# 🔴 SECURITY: Default CELERY_ENABLED adalah 'false' untuk mencegah Celery
#    import chain (circular) saat Django management command dijalankan tanpa
#    docker-compose env vars (misalnya collectstatic, migrate, check).
#    Container celery/beat Wajib set CELERY_ENABLED=true secara eksplisit
#    di docker-compose.yml (sudah dikonfigurasi sebelumnya).
#
import os

CELERY_ENABLED = os.environ.get('CELERY_ENABLED', 'false').lower() in ('true', '1', 'yes')

if CELERY_ENABLED:
    from .celery import app as celery_app  # noqa: F401
    __all__ = ('celery_app',)
