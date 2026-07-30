"""
Django settings for Warungio Marketplace.
Hybrid Django + PHP backend with MySQL, REST Framework, JWT, Channels.
"""

import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# All backends (PHP, Django) share the same root .env file.
try:
    from dotenv import load_dotenv
    root_env = BASE_DIR / '.env'
    django_env = BASE_DIR / 'django_backend' / '.env'
    if root_env.exists():
        load_dotenv(root_env, override=True)
    if django_env.exists():
        load_dotenv(django_env, override=True)
except ImportError:
    pass

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if os.environ.get('DJANGO_DEBUG', 'False').lower() == 'true':
        SECRET_KEY = 'django-insecure-dev-only-key-do-not-use-in-production'
        import warnings
        warnings.warn(
            'DJANGO_SECRET_KEY not set. Using insecure fallback for development only. '
            'Set DJANGO_SECRET_KEY in your .env file for production.',
            RuntimeWarning
        )
    else:
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured(
            'DJANGO_SECRET_KEY environment variable is required in production. '
            'Set a secure random key (at least 50 characters) in your .env or secrets manager.'
        )
DEBUG = os.environ.get('DJANGO_DEBUG', 'False').lower() == 'true'
# In production (DEBUG=False), secure cookie/SSL/HSTS defaults activate automatically.
# Set explicit env vars to override — useful when behind a TLS-terminating proxy
# where SECURE_SSL_REDIRECT is handled upstream (set to 'False' in that case).
SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', str(not DEBUG)).lower() == 'true'
CSRF_COOKIE_SECURE = os.environ.get('CSRF_COOKIE_SECURE', str(not DEBUG)).lower() == 'true'
SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', str(not DEBUG)).lower() == 'true'
SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', '31536000' if not DEBUG else '0'))
ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get(
        'DJANGO_ALLOWED_HOSTS',
        'localhost,127.0.0.1,0.0.0.0,.run.app,warungio.web.id,www.warungio.web.id'
    ).split(',')
    if h.strip()
]

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'csp',
    'channels',
    'django_filters',
    'phonenumber_field',
    'drf_spectacular',
    'drf_spectacular_sidecar',
]

DJANGO_APPS.append('django.contrib.humanize')

LOCAL_APPS = [
    'accounts.apps.AccountsConfig',
    'stores.apps.StoresConfig',
    'products.apps.ProductsConfig',
    'orders.apps.OrdersConfig',
    'payments.apps.PaymentsConfig',
    'analytics.apps.AnalyticsConfig',
    'chat.apps.ChatConfig',
    'notifications.apps.NotificationsConfig',
    'support.apps.SupportConfig',
    'subscriptions.apps.SubscriptionsConfig',
    'refunds',
    # NEW APPS (v2.0.0)
    'suppliers.apps.SuppliersConfig',
    'loyalty.apps.LoyaltyConfig',
    'monitoring.apps.MonitoringConfig',
    'regions.apps.RegionsConfig',
    'inventory.apps.InventoryConfig',
    'core',
    'ai_services.apps.AIServicesConfig',
    'engagement.apps.EngagementConfig',
    'ai_intelligence.apps.AIIntelligenceConfig',
    'seo.apps.SeoConfig',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# =============================================================================
# MIDDLEWARE
# =============================================================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'accounts.middleware.CSRFExemptAPIMiddleware',  # Must be before CsrfViewMiddleware
    'accounts.middleware.CacheControlMiddleware',    # Prevents back-button dashboard access after logout
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'accounts.middleware.RateLimitMiddleware',
    'accounts.middleware.RoleBasedRedirectMiddleware',
]

ROOT_URLCONF = 'config.urls'

# =============================================================================
# TEMPLATES
# =============================================================================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'django_backend' / 'templates',
            BASE_DIR / 'home',
            BASE_DIR / 'auth',
            BASE_DIR / 'buyer',
            BASE_DIR / 'seller',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'accounts.context_processors.site_settings',
                'accounts.context_processors.user_context',
                'seo.context_processors.seo_metadata',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# =============================================================================
# DATABASE - SQLite (dev/fallback) / MySQL (production)
# =============================================================================
import sys

USE_MYSQL = os.environ.get('USE_MYSQL', 'False').lower() == 'true'
if 'test' in sys.argv or any('pytest' in arg for arg in sys.argv) or 'pytest' in sys.modules or os.environ.get('PYTEST_CURRENT_TEST'):
    USE_MYSQL = False

# Database connection type:
#   'tcp'       — Standard TCP connection (docker-compose, local dev)
#   'cloud_sql' — Unix socket via Cloud SQL Auth Proxy / Connector
DB_HOST_TYPE = os.environ.get('DB_HOST_TYPE', 'tcp').lower()

if USE_MYSQL:
    db_options = {
        'charset': 'utf8mb4',
        'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
    }

    # Cloud SQL via Unix socket (Cloud Run + Cloud SQL Auth Proxy / Connector)
    if DB_HOST_TYPE == 'cloud_sql':
        target_socket = os.environ.get(
            'CLOUD_SQL_SOCKET',
            '/cloudsql/' + os.environ.get('CLOUD_SQL_INSTANCE', 'your-project:region:instance')
        )
        short_socket = '/tmp/mysql.sock'
        try:
            if os.path.exists(short_socket) or os.path.islink(short_socket):
                try:
                    os.unlink(short_socket)
                except Exception:
                    pass
            os.symlink(target_socket, short_socket)
            db_options['unix_socket'] = short_socket
        except Exception:
            db_options['unix_socket'] = target_socket
        db_config = {
            'ENGINE': os.environ.get('DB_ENGINE', 'django.db.backends.mysql'),
            'NAME': os.environ.get('DB_NAME', 'warungio_db'),
            'USER': os.environ.get('DB_USER', 'warungio'),
            'PASSWORD': os.environ.get('DB_PASS', ''),
            'HOST': '',  # Not used with Unix socket
            'PORT': '',   # Not used with Unix socket
            'OPTIONS': db_options,
        }
    else:
        # TCP connection (docker-compose, local dev, or Cloud Run via Private IP)
        # IMPORTANT: mysqlclient interprets 'localhost' as Unix socket on Linux
        # which causes (2002) errors on Cloud Run. Convert 'localhost' to '127.0.0.1'
        # to force TCP. Default to '127.0.0.1' instead of 'mysql' for safety.
        raw_host = os.environ.get('DB_HOST', '127.0.0.1')
        db_host = '127.0.0.1' if raw_host and raw_host.lower() == 'localhost' else raw_host

        db_config = {
            'ENGINE': os.environ.get('DB_ENGINE', 'django.db.backends.mysql'),
            'NAME': os.environ.get('DB_NAME', 'warungio_db'),
            'USER': os.environ.get('DB_USER', 'warungio'),
            'PASSWORD': os.environ.get('DB_PASS', ''),
            'HOST': db_host,
            'PORT': os.environ.get('DB_PORT', '3306'),
            'OPTIONS': db_options,
        }

    DATABASES = {'default': db_config}
    # ── Connection Pooling ──
    # CONN_MAX_AGE = 0 (default): close after each request → many TCP handshakes.
    # CONN_MAX_AGE = 60: reuse connection for 60 seconds → saves ~80% handshakes.
    # On 1GB VPS with MariaDB, 60s is safe (max 30 connections configured, won't exhaust pool).
    # Set to 0 if using PgBouncer/ProxySQL or if connections leak.
    DATABASES['default']['CONN_MAX_AGE'] = 60

else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'django_backend' / 'db.sqlite3',
        }
    }

# =============================================================================
# HEALTH CHECK — Safe database test for startup probe
# =============================================================================
# This is consumed by the /health/ endpoint to report DB status.
DATABASE_IS_REQUIRED = os.environ.get('DATABASE_IS_REQUIRED', 'False').lower() == 'true'

# =============================================================================
# REDIS & CHANNELS (WebSocket)
# =============================================================================
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

# Redis Channel Layer is auto-required in production (DEBUG=False).
# In development (DEBUG=True), InMemoryChannelLayer works without Redis.
# Set explicit env var to override — useful for local testing with Redis.
_REDIS_CHANNEL_LAYER_REQUIRED_DEFAULT = 'true' if not DEBUG else 'false'
REDIS_CHANNEL_LAYER_REQUIRED = os.environ.get(
    'REDIS_CHANNEL_LAYER_REQUIRED',
    _REDIS_CHANNEL_LAYER_REQUIRED_DEFAULT
).lower() == 'true'

# Channel Layer — DEFERRED init (zero import-time Redis probes).
# Redis connectivity is checked lazily on first WebSocket access.
if REDIS_CHANNEL_LAYER_REQUIRED:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [REDIS_URL],
                'capacity': 500,
                'expiry': 120,
            },
        },
    }
else:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }

# =============================================================================
# CACHING — Redis in production (DEBUG=False), LocMemCache in development
# =============================================================================
# Redis is available when: explicitly required, or when REDIS_URL points to an
# external host (not localhost), or when DEBUG=False (production mode).
# True when REDIS_URL points away from localhost — covers external hosts AND Docker
# internal service names like 'redis://redis:6379/0' (used in docker-compose).
_redis_url_not_local = bool(REDIS_URL) and 'localhost' not in REDIS_URL and '127.0.0.1' not in REDIS_URL
_redis_available = REDIS_CHANNEL_LAYER_REQUIRED or _redis_url_not_local or not DEBUG

if _redis_available:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'CONNECTION_POOL_CLASS': 'redis.BlockingConnectionPool',
                'CONNECTION_POOL_CLASS_KWARGS': {
                    'max_connections': 4,
                    'timeout': 2,
                },
                'SOCKET_CONNECT_TIMEOUT': 2,
                'SOCKET_TIMEOUT': 2,
                'IGNORE_EXCEPTIONS': True,
            },
            'KEY_PREFIX': 'warungio',
        },
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'warungio-cache',
            'KEY_PREFIX': 'warungio',
        },
    }

# Production-only: use Redis for session storage (saves database writes)
if _redis_available:
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'
    SESSION_COOKIE_AGE = 86400 * 7  # 7 days (reduced from default 2 weeks)

# Jika Redis tidak tersedia, session tetap pakai database default Django

CACHE_TTL = 60 * 15  # 15 minutes default

# =============================================================================
# VOICE NOTIFICATION (Web Speech API — browser-native TTS, no external API)
# =============================================================================
# Uses the Web Speech API (SpeechSynthesis) built into all modern browsers.
# No API key, no cloud service, no SDK — 100% browser-native.
# Toggle this off to disable all voice notification broadcasts server-wide.
VOICE_NOTIFICATION_ENABLED = os.environ.get(
    'VOICE_NOTIFICATION_ENABLED', 'true'
).lower() == 'true'

# =============================================================================
# CELERY (Async Tasks)
# =============================================================================
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Jakarta'

# ── Development Mode: run tasks synchronously (no Redis required) ──
# In DEBUG mode, execute tasks in-process so the app works without Redis.
# Production sets this to False so tasks run via Celery workers.
CELERY_TASK_ALWAYS_EAGER = DEBUG
CELERY_TASK_EAGER_PROPAGATES = DEBUG

# ── Task Execution Time Limits ──
# Soft time limit: task gets a SoftTimeLimitExceeded exception (can catch & cleanup)
# Hard time limit: worker kills the task process (prevents hung tasks from blocking)
CELERY_TASK_SOFT_TIME_LIMIT = 240  # 4 minutes
CELERY_TASK_TIME_LIMIT = 300       # 5 minutes

# ── Result Backend ──
# Auto-expire task results after 1 hour to prevent Redis memory growth.
# 24h (86400s) terlalu lama untuk 1GB RAM — result task tidak perlu disimpan >1 jam.
CELERY_RESULT_EXPIRES = 1800  # 30 minutes (was 3600) — faster cleanup for 1GB RAM

# ── Task Acknowledgment ──
# If True, task is only removed from broker after it completes (not when received).
# If the worker crashes mid-task, the task is re-delivered to another worker.
CELERY_TASK_ACKS_LATE = True

# ── Worker Behavior ──
# Prefetch multiplier = 1 ensures fair distribution (one task at a time per worker).
# Default is 4, which can cause uneven load across workers.
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

# ── Task Memory Management ──
# Restart worker process after 500 tasks to prevent memory leaks.
# 500 tasks x ~2MB leak per task = max 1GB over worker lifetime
# Combined with concurrency=1, this effectively manages memory.
# Worker Concurrency: single worker for 1GB RAM VPS
CELERY_WORKER_CONCURRENCY = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 200  # Restart every 200 tasks to prevent memory bloat on 1GB VPS
CELERY_WORKER_HIJACK_ROOT_LOGGER = False

# ── Task Serialization ──
# Only allow JSON for security (prevents pickle-based exploits)
CELERY_TASK_ACCEPT_CONTENT = ['json']

# ── Default Queue ──
# Explicit queue name for observability. Celery worker will listen here by default.
CELERY_TASK_DEFAULT_QUEUE = 'warungio_default'
CELERY_TASK_DEFAULT_EXCHANGE = 'warungio_default'
CELERY_TASK_DEFAULT_ROUTING_KEY = 'warungio_default'

# ── Task Rejection on Worker Lost ──
# When a worker crashes/restarts while processing a task (acks_late=True),
# reject the unacknowledged message so it can be redelivered to another worker.
CELERY_TASK_REJECT_ON_WORKER_LOST = True

# ── Task ACK on Failure ──
# Acknowledge tasks even when they fail. Prevents permanently failing tasks
# from remaining on the broker and being re-delivered after visibility_timeout.
# Combined with autoretry_for, this ensures transient failures retry while
# business logic errors are acknowledged and logged (not re-queued forever).
CELERY_TASK_ACKS_ON_FAILURE_OR_TIMEOUT = True

# ── Task Events (for monitoring tools like Flower, Prometheus) ──
# Sends task state changes (sent, received, started, succeeded, failed, retried)
# as Celery events. Required for Flower dashboards and Prometheus metrics.
CELERY_WORKER_SEND_TASK_EVENTS = True
CELERY_TASK_SEND_SENT_EVENT = True
CELERY_TASK_TRACK_STARTED = True

# ── Broker Transport Options ──
# visibility_timeout: If a worker fetches a task then crashes before ACKing,
# the task becomes visible to other workers after this timeout.
# Set to match CELERY_TASK_TIME_LIMIT (300s) + 60s buffer.
CELERY_BROKER_TRANSPORT_OPTIONS = {
    'visibility_timeout': 360,
    'global_keyprefix': 'warungio_celery_',
    'socket_timeout': 5,
    'socket_connect_timeout': 5,
    'retry_on_timeout': True,
    'health_check_interval': 30,
}

# ── Task Annotations (auto-set time limits per task name pattern) ──
# Only tasks that might exceed the global 240s limit need explicit annotations.
# All other tasks inherit CELERY_TASK_SOFT_TIME_LIMIT / CELERY_TASK_TIME_LIMIT.
CELERY_TASK_ANNOTATIONS = {
    'payments.tasks.*': {
        'soft_time_limit': 240,
        'time_limit': 300,
    },
    'ai_intelligence.tasks.*': {
        'soft_time_limit': 120,
        'time_limit': 180,
    },
    'engagement.tasks.*': {
        'soft_time_limit': 120,
        'time_limit': 180,
    },
    'ai_services.tasks.*': {
        'soft_time_limit': 180,
        'time_limit': 240,
    },
}

# ── Beat Schedule Storage ──
# Store schedule in DB so it persists across container restarts.
# Requires django-celery-beat to be installed.
# Fallback to file-based PersistentScheduler if not available.
CELERY_BEAT_SCHEDULER = 'celery.beat.PersistentScheduler'
CELERY_BEAT_SCHEDULE_FILENAME = '/tmp/celerybeat-schedule'  # Avoids DB locks on 1GB VPS

# =============================================================================
# AUTHENTICATION
# =============================================================================
AUTH_USER_MODEL = 'accounts.User'
LOGIN_URL = '/'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTHENTICATION_BACKENDS = [
    'accounts.backends.EmailBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# =============================================================================
# REST FRAMEWORK + JWT
# =============================================================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'MAX_PAGE_SIZE': 100,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.ScopedRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'otp': '30/minute',  # 30/min allows legitimate multi-step OTP flows without false throttling (was 5/min)
        'login': '10/minute',
        'admin_login': '5/minute',  # Tighter throttle for admin login security
    },
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    # BrowsableAPIRenderer disabled in production to save bandwidth & memory
    'EXCEPTION_HANDLER': 'accounts.exceptions.custom_exception_handler',
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=2),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUTH_HEADER_TYPES': ('Bearer',),  # Only Bearer (not JWT) to avoid OpenAPI schema warnings
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'JTI_CLAIM': 'jti',
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(hours=2),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=30),
}

# =============================================================================
# CORS
# =============================================================================
# Never allow all origins in production — explicit CORS_ALLOWED_ORIGINS must be set.
CORS_ALLOW_ALL_ORIGINS = DEBUG and not os.environ.get('CORS_ALLOWED_ORIGINS')
CORS_ALLOWED_ORIGINS = os.environ.get(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:3000,http://localhost:8000,http://localhost:5000,https://warungio.web.id,https://www.warungio.web.id'
).split(',')
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ['DELETE', 'GET', 'OPTIONS', 'PATCH', 'POST', 'PUT']
CORS_ALLOW_HEADERS = [
    'accept', 'authorization', 'content-type', 'x-csrftoken',
    'x-requested-with', 'x-csrf-token',
]

# CSRF Trusted Origins — must be set explicitly for production
# Default includes localhost for development; in production, set via env var.
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get(
        'CSRF_TRUSTED_ORIGINS',
        'http://localhost,http://127.0.0.1,http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000,http://127.0.0.1:3000,https://warungio.web.id,https://www.warungio.web.id'
    ).split(',')
    if o.strip()
]

# =============================================================================
# INTERNATIONALIZATION
# =============================================================================
LANGUAGE_CODE = 'id'
TIME_ZONE = 'Asia/Jakarta'
USE_I18N = True
USE_TZ = True

# =============================================================================
# STATIC & MEDIA FILES
# =============================================================================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'django_backend' / 'static',
]

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'django_backend' / 'media'

# =============================================================================
# =============================================================================
# DOWNLOAD APP SYSTEM — APK & iOS Configuration
# =============================================================================
# Centralized configuration for direct app download system.
# To update: upload new build, then change the version/path below.
APP_DOWNLOAD_ENABLED = os.environ.get('APP_DOWNLOAD_ENABLED', 'True').lower() == 'true'

# Android APK Configuration
# Path to the APK file on the server (relative to BASE_DIR or absolute)
ANDROID_APK_PATH = os.environ.get(
    'ANDROID_APK_PATH',
    str(BASE_DIR / 'django_backend' / 'downloads' / 'warungio.apk')
)
ANDROID_APK_VERSION = os.environ.get('ANDROID_APK_VERSION', '1.0.0')
ANDROID_APK_BUILD_NUMBER = os.environ.get('ANDROID_APK_BUILD_NUMBER', '1')
ANDROID_APK_PACKAGE_NAME = os.environ.get(
    'ANDROID_APK_PACKAGE_NAME',
    'com.warungio.marketplace'
)
# SHA256 hash of the APK for integrity verification (empty = skip check)
ANDROID_APK_SHA256 = os.environ.get('ANDROID_APK_SHA256', '')

# iOS Configuration (future distribution — TestFlight, App Store, or OTA manifest)
IOS_IPA_PATH = os.environ.get('IOS_IPA_PATH', '')
IOS_IPA_VERSION = os.environ.get('IOS_IPA_VERSION', '1.0.0')
IOS_IPA_BUILD_NUMBER = os.environ.get('IOS_IPA_BUILD_NUMBER', '1')
IOS_BUNDLE_ID = os.environ.get('IOS_BUNDLE_ID', 'com.warungio.marketplace')
# For Apple App Store distribution, set the URL here. When configured,
# iOS users will be redirected here instead of downloading the IPA.
IOS_DISTRIBUTION_URL = os.environ.get('IOS_DISTRIBUTION_URL', '')
# For OTA (Over-The-Air) enterprise distribution via manifest plist
IOS_MANIFEST_URL = os.environ.get('IOS_MANIFEST_URL', '')
IOS_MANIFEST_PATH = os.environ.get(
    'IOS_MANIFEST_PATH',
    str(BASE_DIR / 'django_backend' / 'downloads' / 'manifest.plist')
)

# General download settings
DOWNLOAD_ANALYTICS_ENABLED = os.environ.get(
    'DOWNLOAD_ANALYTICS_ENABLED', 'True'
).lower() == 'true'
DOWNLOAD_CHUNK_SIZE = 8192  # 8KB chunks for streaming
DOWNLOAD_CACHE_SECONDS = 3600  # 1 hour cache for download metadata

# In production, enable X-Accel-Redirect so nginx serves the file directly
# without passing through Django's Python process (more efficient for large APKs).
# Default: True in production (DEBUG=False), False in development.
# nginx must have the /download-files/ internal location configured (it does).
_use_x_accel_default = 'True' if not DEBUG else 'False'
USE_X_ACCEL_REDIRECT = os.environ.get(
    'USE_X_ACCEL_REDIRECT', _use_x_accel_default
).lower() == 'true'

# =============================================================================
# FILE UPLOAD SECURITY
# =============================================================================
FILE_UPLOAD_MAX_MEMORY_SIZE = 2097152  # 2MB (reduced from 5MB for 1GB RAM)
FILE_UPLOAD_PERMISSIONS = 0o644
DATA_UPLOAD_MAX_MEMORY_SIZE = 2097152  # 2MB (reduced from 5MB for 1GB RAM)
DATA_UPLOAD_MAX_NUMBER_FIELDS = 100

ALLOWED_IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'webp']
ALLOWED_IMAGE_MIME_TYPES = [
    'image/jpeg', 'image/png', 'image/gif', 'image/webp'
]

# =============================================================================
# SOCIAL AUTHENTICATION
# =============================================================================
GOOGLE_CLIENT_ID = os.environ.get(
    'GOOGLE_CLIENT_ID',
    'your-google-client-id.apps.googleusercontent.com'
)
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')

FACEBOOK_APP_ID = os.environ.get('FACEBOOK_APP_ID', '')
FACEBOOK_APP_SECRET = os.environ.get('FACEBOOK_APP_SECRET', '')

APPLE_CLIENT_ID = os.environ.get(
    'APPLE_CLIENT_ID',
    ''
)
APPLE_CLIENT_SECRET = os.environ.get('APPLE_CLIENT_SECRET', '')
APPLE_KEY_ID = os.environ.get('APPLE_KEY_ID', '')
APPLE_TEAM_ID = os.environ.get('APPLE_TEAM_ID', '')
APPLE_PRIVATE_KEY = os.environ.get('APPLE_PRIVATE_KEY', '')

# =============================================================================
# GOOGLE MAPS API
# =============================================================================
GOOGLE_MAPS_API_KEY = os.environ.get(
    'GOOGLE_MAPS_API_KEY',
    ''
)

# =============================================================================
# GOOGLE SEARCH CONSOLE
# =============================================================================
GOOGLE_SITE_VERIFICATION = os.environ.get(
    'GOOGLE_SITE_VERIFICATION',
    ''
)

# =============================================================================
# BINDERBYTE — Courier Tracking API
# =============================================================================
BINDERBYTE_API_KEY = os.environ.get('BINDERBYTE_API_KEY', '')
BINDERBYTE_BASE_URL = 'https://api.binderbyte.com/v1'

# =============================================================================
# GRABEXPRESS — Delivery API Integration
# =============================================================================
GRAB_CLIENT_ID = os.environ.get('GRAB_CLIENT_ID', '')
GRAB_CLIENT_SECRET = os.environ.get('GRAB_CLIENT_SECRET', '')
GRAB_API_URL = os.environ.get('GRAB_API_URL', 'https://api.grab.com/v1')
GRAB_SANDBOX_URL = os.environ.get('GRAB_SANDBOX_URL', 'https://partner-api.stg-myteksi.com/v1')
GRAB_IS_SANDBOX = os.environ.get('GRAB_IS_SANDBOX', 'True').lower() == 'true'

# GrabExpress service types (Instant, SameDay, etc.)
# These are enabled/disabled based on Grab API availability
GRAB_SERVICE_TYPES = os.environ.get('GRAB_SERVICE_TYPES', 'Instant,SameDay,Regular').split(',')

# Grab webhook secret for payload signature verification
GRAB_WEBHOOK_SECRET = os.environ.get('GRAB_WEBHOOK_SECRET', '')

# =============================================================================
# GOJEK (GOSEND) — Delivery API Integration
# =============================================================================
GOJEK_CLIENT_ID = os.environ.get('GOJEK_CLIENT_ID', '')
GOJEK_CLIENT_SECRET = os.environ.get('GOJEK_CLIENT_SECRET', '')
GOJEK_API_URL = os.environ.get('GOJEK_API_URL', 'https://api.gojek.com/v1')
GOJEK_SANDBOX_URL = os.environ.get('GOJEK_SANDBOX_URL', 'https://api.gojek.com/sandbox/v1')
GOJEK_IS_SANDBOX = os.environ.get('GOJEK_IS_SANDBOX', 'True').lower() == 'true'

# GoSend service types
GOJEK_SERVICE_TYPES = os.environ.get('GOJEK_SERVICE_TYPES', 'Instant,SameDay').split(',')

# Gojek webhook secret for payload signature verification
GOJEK_WEBHOOK_SECRET = os.environ.get('GOJEK_WEBHOOK_SECRET', '')

# =============================================================================
# OTP CONFIGURATION
# =============================================================================
OTP_LENGTH = 6
OTP_EXPIRE_MINUTES = int(os.environ.get('OTP_EXPIRE_MINUTES', 15))
OTP_COOLDOWN_SECONDS = 60  # Resend cooldown
OTP_MAX_ATTEMPTS = 5  # Max verify attempts before lockout
OTP_LOCKOUT_MINUTES = 60

# =============================================================================
# ACCOUNT LOCKOUT (Brute Force Protection)
# =============================================================================
LOGIN_MAX_ATTEMPTS = int(os.environ.get('LOGIN_MAX_ATTEMPTS', 5))
LOGIN_LOCKOUT_MINUTES = int(os.environ.get('LOGIN_LOCKOUT_MINUTES', 15))

# =============================================================================
# WHATSAPP OTP DELIVERY
# =============================================================================
WHATSAPP_PROVIDER = os.environ.get('WHATSAPP_PROVIDER', '')  # fonnte, twilio, wati, direct
WHATSAPP_API_KEY = os.environ.get('WHATSAPP_API_KEY', '')
WHATSAPP_API_URL = os.environ.get('WHATSAPP_API_URL', '')
WHATSAPP_PHONE_NUMBER_ID = os.environ.get('WHATSAPP_PHONE_NUMBER_ID', '')
WHATSAPP_BASE_URL = os.environ.get('WHATSAPP_BASE_URL', 'https://wati.com/api/v1')

# Fonnte (Indonesian WhatsApp Gateway)
# Get API key from: https://docs.fonnte.com
# API key format: starts with 'fsk_'
WHATSAPP_FONNTE_API_KEY = os.environ.get('WHATSAPP_FONNTE_API_KEY', '')

# Twilio (for WhatsApp via Twilio)
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')

# =============================================================================
# MIDTRANS PAYMENT
# =============================================================================
MIDTRANS_SERVER_KEY = os.environ.get('MIDTRANS_SERVER_KEY', '')
MIDTRANS_CLIENT_KEY = os.environ.get('MIDTRANS_CLIENT_KEY', '')
MIDTRANS_MERCHANT_ID = os.environ.get('MIDTRANS_MERCHANT_ID', '')
MIDTRANS_IS_PRODUCTION = os.environ.get('MIDTRANS_IS_PRODUCTION', 'False').lower() == 'true'
# Dynamic Snap URL based on environment — production vs sandbox
if MIDTRANS_IS_PRODUCTION:
    MIDTRANS_SNAP_URL = 'https://app.midtrans.com/snap/v1/transactions'
else:
    MIDTRANS_SNAP_URL = 'https://app.sandbox.midtrans.com/snap/v1/transactions'

# =============================================================================
# EMAIL (OTP Delivery)
# =============================================================================
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend'
)
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')

DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'warungio.id@gmail.com')

# =============================================================================
# IMAP (Inbox Audit — email delivery verification)
# =============================================================================
IMAP_HOST = os.environ.get('IMAP_HOST', '')
IMAP_PORT = int(os.environ.get('IMAP_PORT', 993))
IMAP_USER = os.environ.get('IMAP_USER', '')
IMAP_PASSWORD = os.environ.get('IMAP_PASSWORD', '')
IMAP_SSL = os.environ.get('IMAP_SSL', 'True').lower() == 'true'

# =============================================================================
# LOGGING
# =============================================================================

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ── Production Logging ──
# File handler hanya aktif jika DJANGO_DEBUG=True.
# Production: console-only (Docker logs) untuk hemat I/O dan disk.

# ── PRODUCTION: console-only, WARNING+ level (hemat I/O dan disk) ──
# ── DEVELOPMENT: console DEBUG+INFO + file WARNING+INFO ──
# File handler mati di production untuk mencegah disk penuh (1GB RAM VPS).

if not DEBUG:
    # Production: console-only, WARNING+ level
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                'format': '{levelname} {asctime} {module} {message}',
                'style': '{',
            },
        },
        'handlers': {
            'console': {
                'level': 'WARNING',
                'class': 'logging.StreamHandler',
                'formatter': 'verbose',
            },
        },
        'loggers': {
            'django': {
                'handlers': ['console'],
                'level': 'WARNING',
                'propagate': True,
            },
            'django_backend': {
                'handlers': ['console'],
                'level': 'WARNING',
                'propagate': True,
            },
        },
    }
else:
    # Development: console + file handler
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                'format': '{levelname} {asctime} {module} {message}',
                'style': '{',
            },
            'simple': {
                'format': '{levelname} {message}',
                'style': '{',
            },
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'verbose',
            },
            'file': {
                'level': 'WARNING',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': LOG_DIR / 'django.log',
                'maxBytes': 10 * 1024 * 1024,
                'backupCount': 3,
                'formatter': 'verbose',
            },
        },
        'loggers': {
            'django': {
                'handlers': ['console', 'file'],
                'level': 'INFO',
                'propagate': True,
            },
            'django_backend': {
                'handlers': ['console', 'file'],
                'level': 'DEBUG',
                'propagate': True,
            },
        },
    }

# =============================================================================
# SECURITY SETTINGS (Production)
# =============================================================================
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
SECURE_HSTS_PRELOAD = SECURE_HSTS_SECONDS > 0
SECURE_BROWSER_XSS_FILTER = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# =============================================================================
# CONTENT SECURITY POLICY (CSP)
# =============================================================================
# Strict CSP to prevent XSS while allowing required third-party services.
# Google AdSense, Google Fonts, Google Maps, Midtrans, and CDNJS are whitelisted.
# Using django-csp >= 4.0 format (CONTENT_SECURITY_POLICY dict).

_CSP_DIRECTIVES = {
    'default-src': ("'self'",),
    'script-src': (
        "'self'",
        "'unsafe-inline'",  # Required for inline scripts in templates
        "'unsafe-eval'",    # Required by Chart.js, TensorFlow.js
        "https://pagead2.googlesyndication.com",   # Google AdSense
        "https://googleads.g.doubleclick.net",      # AdSense dynamic ads
        "https://www.gstatic.com",                  # Google Identity, AdSense assets
        "https://accounts.google.com",              # Google OAuth GSI (auth pages)
        "https://cdnjs.cloudflare.com",             # Font Awesome icons (seller/buyer)
        "https://cdn.jsdelivr.net",                 # Chart.js, Tesseract.js, TensorFlow.js, QR
        "https://unpkg.com",                       # Leaflet maps, AOS animations
        "https://app.sandbox.midtrans.com",         # Midtrans Sandbox
        "https://app.midtrans.com",                 # Midtrans Production
        "https://maps.googleapis.com",              # Google Maps
    ),
    'style-src': (
        "'self'",
        "'unsafe-inline'",  # Inline styles from templates
        "https://fonts.googleapis.com",             # Google Fonts
        "https://cdnjs.cloudflare.com",             # Font Awesome CSS
        "https://cdn.jsdelivr.net",                 # Chart.js styles (admin dashboard)
        "https://unpkg.com",                       # Leaflet CSS (buyer order tracking)
        "https://pagead2.googlesyndication.com",    # AdSense styles
    ),
    'img-src': (
        "'self'",
        "data:",
        "blob:",
        "https:",  # Allow images from any HTTPS source
        "https://tpc.googlesyndication.com",  # AdSense image delivery
    ),
    'font-src': (
        "'self'",
        "data:",
        "https://fonts.gstatic.com",
        "https://cdnjs.cloudflare.com",
    ),
    'connect-src': (
        "'self'",
        "https://pagead2.googlesyndication.com",
        "https://googleads.g.doubleclick.net",
        "https://accounts.google.com",              # Google OAuth token exchange
        "https://www.gstatic.com",
        "https://app.sandbox.midtrans.com",
        "https://app.midtrans.com",
        "https://cdn.jsdelivr.net",                 # Model weights (TensorFlow.js)
        "wss://warungio.web.id",
        "ws://localhost:8000",
        "wss://localhost:8000",
    ),
    'frame-src': (
        "'self'",
        "https://pagead2.googlesyndication.com",
        "https://googleads.g.doubleclick.net",
        "https://accounts.google.com",              # Google OAuth popup
        "https://app.sandbox.midtrans.com",         # Midtrans Snap iframe
        "https://app.midtrans.com",                 # Midtrans Snap iframe
        "https://maps.googleapis.com",              # Google Maps embed
    ),
    'media-src': ("'self'", "blob:", "data:"),
    'object-src': ("'none'",),
    'base-uri': ("'self'",),
    'form-action': ("'self'", "https://app.sandbox.midtrans.com", "https://app.midtrans.com"),
    'frame-ancestors': ("'self'",),
    'worker-src': ("'self'", "blob:"),
    'manifest-src': ("'self'",),
}

if not DEBUG:
    CONTENT_SECURITY_POLICY = {
        'DIRECTIVES': _CSP_DIRECTIVES,
    }
else:
    # Development: report-only mode (won't block, will log warnings)
    CONTENT_SECURITY_POLICY = {
        'DIRECTIVES': _CSP_DIRECTIVES,
    }

# Register CSP middleware early in chain (after SecurityMiddleware, before WhiteNoise)
# Explicit insertion ensures CSP header is set before any middleware that might read it
MIDDLEWARE.insert(1, 'csp.middleware.CSPMiddleware')

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
# CSRF_COOKIE_HTTPONLY = False
# Safety note: CSRF_COOKIE_HTTPONLY is intentionally False to allow JavaScript
# to read the CSRF token cookie and send it as X-CSRFToken header.
# This is the standard Django+DRF pattern for SPAs with dual auth (JWT + session).
# The primary auth is JWT Bearer token, so CSRF exposure risk is minimal.
# Browser SameSite=Lax provides additional CSRF protection.
# If the app transitions to 100% JWT-only, CSRF middleware can be exempted for API paths.
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = 'Lax'

# =============================================================================
# DEFAULT PRIMARY KEY FIELD TYPE
# =============================================================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# =============================================================================
# DRF-SPECTACULAR — OpenAPI / Swagger Documentation
# =============================================================================
SPECTACULAR_SETTINGS = {
    'TITLE': 'Warungio Marketplace API',
    'DESCRIPTION': (
        'Warungio — Hyperlocal marketplace untuk kebutuhan harian dan produk segar.\n\n'
        '**Fitur:** Manajemen akun, produk, pesanan, pengiriman hyperlocal '
        '(GoSend, GrabExpress, Maxim, Antar Sendiri), pembayaran Midtrans, '
        'analitik, notifikasi realtime, dan chat.\n\n'
        '**Autentikasi:** JWT Bearer token. Dapatkan token via `/api/token/` endpoint.'
    ),
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': False,
    },
    'TAGS': [
        {'name': 'Auth', 'description': 'Autentikasi, registrasi, OTP, reset password'},
        {'name': 'Users', 'description': 'Profil pengguna, sosial accounts'},
        {'name': 'Stores', 'description': 'Manajemen toko'},
        {'name': 'Products', 'description': 'Produk, kategori, review, promo, quality checks'},
        {'name': 'Cart', 'description': 'Keranjang belanja'},
        {'name': 'Orders', 'description': 'Pesanan, checkout, pembatalan'},
        {'name': 'Shipping', 'description': 'Metode pengiriman hyperlocal (GoSend, GrabExpress, Maxim, Antar Sendiri)'},
        {'name': 'Delivery', 'description': 'Status pengiriman & tracking hyperlocal'},
        {'name': 'Payments', 'description': 'Pembayaran Midtrans'},
        {'name': 'Analytics', 'description': 'Dashboard analitik seller'},
        {'name': 'Chat', 'description': 'Pesan realtime chat'},
        {'name': 'Notifications', 'description': 'Notifikasi push & realtime'},
        {'name': 'Engagement', 'description': 'AI Engagement & Retention Engine'},
        {'name': 'Support', 'description': 'Tiket bantuan & support center'},
        {'name': 'Subscriptions', 'description': 'Langganan toko'},
    ],
    'SWAGGER_UI_DIST': 'SIDECAR',
    'SWAGGER_UI_FAVICON_HREF': 'SIDECAR',
    'POSTPROCESSING_HOOKS': [
        'drf_spectacular.hooks.postprocess_schema_enums',
    ],
    # Schema uses 'Bearer' only (SIMPLE_JWT also uses 'Bearer' only)
    # COMPONENT_SPLIT_REQUEST scopes enum schemas per request/response
    # component, preventing global enum name collisions across models.
    'COMPONENT_SPLIT_REQUEST': True,
    # ENUM_NAME_OVERRIDES resolves enum naming collisions by explicitly naming
    # shared enum values that appear under the same field name but with
    # different choice sets across multiple models/components.
    'ENUM_NAME_OVERRIDES': {
        # Priority collisions: Notification/NotificationTemplate use str,
        # NotificationQueue/EngagementSignal use int with different sets
        'NotificationPriorityEnum': [
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('urgent', 'Urgent'),
        ],
        'QueuePriorityEnum': [
            (0, 'Low'),
            (1, 'Normal'),
            (2, 'High'),
            (3, 'Urgent'),
        ],
        # Reason collision: Refund.reason (8 values with labels) vs
        # CancelOrderSerializer.reason (6 plain string values)
        'RefundReasonEnum': [
            ('wrong_product', 'Produk Tidak Sesuai'),
            ('product_damaged', 'Produk Rusak/Cacat'),
            ('not_as_described', 'Tidak Sesuai Deskripsi'),
            ('expired', 'Produk Kadaluarsa'),
            ('missing_items', 'Barang Kurang'),
            ('defective', 'Produk Cacat'),
            ('change_mind', 'Berubah Pikiran'),
            ('other', 'Lainnya'),
        ],
        'BuyerCancelReasonEnum': [
            'change_mind',
            'found_cheaper',
            'delivery_too_long',
            'wrong_address',
            'duplicate_order',
            'other',
        ],
        # Status collisions: Store vs Supplier have different status options
        'StoreStatusEnum': [
            ('pending', 'Pending'),
            ('active', 'Active'),
            ('rejected', 'Rejected'),
            ('suspended', 'Suspended'),
        ],
        'SupplierStatusEnum': [
            ('pending', 'Pending'),
            ('active', 'Active'),
            ('suspended', 'Suspended'),
            ('blacklisted', 'Blacklisted'),
            ('inactive', 'Inactive'),
        ],
        # Channel collision: Campaign channel vs other channel fields
        'CampaignChannelEnum': [
            ('push', 'Push Notification'),
            ('email', 'Email'),
            ('in_app', 'In-App Notification'),
            ('whatsapp', 'WhatsApp'),
            ('sms', 'SMS'),
        ],
        # Type collision: Regency type vs Village type
        'RegencyTypeEnum': [
            ('kabupaten', 'Kabupaten'),
            ('kota', 'Kota'),
        ],
    },
}

# =============================================================================
# GEMINI / VERTEX AI — Unified AI Services
# =============================================================================
# Gemini API key — primary AI provider for all Warungio AI features
# Supports multiple env var names for legacy compatibility (case-insensitive search):
#   GEMINI_KEY (preferred), Gemini_key, GOOGLE_API_KEY, VERTEX_KEY, Vertex_key
_GEMINI_KEY = os.environ.get('GEMINI_KEY', '')
if not _GEMINI_KEY:
    _GEMINI_KEY = os.environ.get('Gemini_key', '')
if not _GEMINI_KEY:
    _GEMINI_KEY = os.environ.get('GOOGLE_API_KEY', '')
if not _GEMINI_KEY:
    _GEMINI_KEY = os.environ.get('VERTEX_KEY', '')
if not _GEMINI_KEY:
    _GEMINI_KEY = os.environ.get('Vertex_key', '')
GEMINI_KEY = _GEMINI_KEY
# Vertex AI key — fallback/alternative AI provider
VERTEX_KEY = _GEMINI_KEY

GCP_PROJECT_ID = os.environ.get('GCP_PROJECT_ID', 'your-gcp-project')
GCP_REGION = os.environ.get('GCP_REGION', 'us-central1')

# Vertex AI endpoint configuration
VERTEX_AI_ENDPOINT_ID = os.environ.get('VERTEX_AI_ENDPOINT_ID', 'openapi')
VERTEX_AI_MODEL = os.environ.get(
    'VERTEX_AI_MODEL', 
    'meta/llama-3.3-70b-instruct-maas'
)

# AI Chat configuration
AI_CHAT_ENABLED = os.environ.get('AI_CHAT_ENABLED', 'True').lower() == 'true'
AI_CHAT_MIN_CONFIDENCE = 0.7  # 70% confidence threshold
AI_CHAT_ESCALATION_ENABLED = os.environ.get(
    'AI_CHAT_ESCALATION_ENABLED', 
    'True'
).lower() == 'true'

# AI Services Caching
AI_CACHE_TTL = 3600  # 1 hour default cache for AI responses

# =============================================================================
# PUSH NOTIFICATIONS — FCM / Web Push
# =============================================================================
# Firebase Cloud Messaging Server Key (Legacy HTTP protocol)
FCM_SERVER_KEY = os.environ.get('FCM_SERVER_KEY', '')
# Firebase service account JSON path (for FCM HTTP v1 API)
FCM_CREDENTIALS = os.environ.get('FCM_CREDENTIALS', '')

# Web Push (VAPID) — for PWA browser notifications
# Generate: npx web-push generate-vapid-keys
VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY', '')
VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY', '')
VAPID_CLAIM_EMAIL = os.environ.get('VAPID_CLAIM_EMAIL', 'warungio.id@gmail.com')

# =============================================================================
# ENGAGEMENT ENGINE CONFIGURATION
# =============================================================================
# Cooldown interval for processing notification queue (seconds)
ENGAGEMENT_QUEUE_PROCESS_INTERVAL = int(os.environ.get('ENGAGEMENT_QUEUE_PROCESS_INTERVAL', 30))
# Maximum notifications to process per queue run
ENGAGEMENT_QUEUE_BATCH_SIZE = int(os.environ.get('ENGAGEMENT_QUEUE_BATCH_SIZE', 20))  # Reduced for 1GB VPS
# Batch profile update interval (hours)
ENGAGEMENT_PROFILE_UPDATE_INTERVAL = int(os.environ.get('ENGAGEMENT_PROFILE_UPDATE_INTERVAL', 6))
# Max at-risk users to scan per run
ENGAGEMENT_AT_RISK_SCAN_LIMIT = int(os.environ.get('ENGAGEMENT_AT_RISK_SCAN_LIMIT', 25))  # Reduced for 1GB VPS
# Min inactive days before marking user as at-risk
ENGAGEMENT_MIN_INACTIVE_DAYS = int(os.environ.get('ENGAGEMENT_MIN_INACTIVE_DAYS', 7))
