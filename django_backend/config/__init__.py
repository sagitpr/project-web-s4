# Celery — NONAKTIF untuk VPS 1GB RAM
# Aktifkan dengan set CELERY_ENABLED=true di .env
# atau dengan mengubah CELERY_ENABLED di bawah menjadi True
#
# from .celery import app as celery_app
# __all__ = ('celery_app',)

import os

CELERY_ENABLED = os.environ.get('CELERY_ENABLED', 'false').lower() in ('true', '1', 'yes')

if CELERY_ENABLED:
    from .celery import app as celery_app  # noqa: F401
    __all__ = ('celery_app',)
