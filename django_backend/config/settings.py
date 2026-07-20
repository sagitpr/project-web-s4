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

SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-w4rungio-m4rk3tpl4c3-pr0duct10n-k3y-r3pl4c3-m3-1n-3nv'  # 48 chars, meets 32-byte minimum
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
        'localhost,127.0.0.1,0.0.0.0,.run.app'
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
    'channels',
    'django_filters',
    'phonenumber_field',
    'drf_spectacular',
    'drf_spectacular_sidecar',
]

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
                'capacity': 1500,
                'expiry': 60,
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
                    'max_connections': 8,
                    'timeout': 3,
                },
                'SOCKET_CONNECT_TIMEOUT': 3,
                'SOCKET_TIMEOUT': 3,
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
CELERY_RESULT_EXPIRES = 3600

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
CELERY_WORKER_MAX_TASKS_PER_CHILD = 500
CELERY_WORKER_HIJACK_ROOT_LOGGER = False

# ── Task Serialization ──
# Only allow JSON for security (prevents pickle-based exploits)
CELERY_TASK_ACCEPT_CONTENT = ['json']

# ── Default Queue ──
# Explicit queue name for observability. Celery worker will listen here by default.
CELERY_TASK_DEFAULT_QUEUE = 'warungio_default'
CELERY_TASK_DEFAULT_EXCHANGE = 'warungio_default'
CELERY_TASK_DEFAULT_ROUTING_KEY = 'warungio_default'

# ── Beat Schedule Storage ──
# Store schedule in DB so it persists across container restarts.
# Requires django-celery-beat to be installed.
# Fallback to file-based PersistentScheduler if not available.
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

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
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'otp': '5/minute',
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
    'http://localhost:3000,http://localhost:8000,http://localhost:5000'
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
        'http://localhost,http://127.0.0.1,http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000,http://127.0.0.1:3000'
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
# FILE UPLOAD SECURITY
# =============================================================================
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
FILE_UPLOAD_PERMISSIONS = 0o644
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
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
# BINDERBYTE — Courier Tracking API
# =============================================================================
BINDERBYTE_API_KEY = os.environ.get('BINDERBYTE_API_KEY', '')
BINDERBYTE_BASE_URL = 'https://api.binderbyte.com/v1'

# Set BINDERBYTE_API_KEY in your .env file to enable real tracking.
# Get your API key at: https://binderbyte.com
# When not set, the system falls back to mock tracking data for development.

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

DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@warungio.com')

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
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

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
    # Fix enum naming collisions for fields used across multiple models
    'ENUM_NAME_OVERRIDES': {
        # Field names that appear in multiple models with different choices
        # Each entry maps component_name -> { field_name: named_enum_class }
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
VAPID_CLAIM_EMAIL = os.environ.get('VAPID_CLAIM_EMAIL', 'admin@warungio.com')

# =============================================================================
# ENGAGEMENT ENGINE CONFIGURATION
# =============================================================================
# Cooldown interval for processing notification queue (seconds)
ENGAGEMENT_QUEUE_PROCESS_INTERVAL = int(os.environ.get('ENGAGEMENT_QUEUE_PROCESS_INTERVAL', 30))
# Maximum notifications to process per queue run
ENGAGEMENT_QUEUE_BATCH_SIZE = int(os.environ.get('ENGAGEMENT_QUEUE_BATCH_SIZE', 50))
# Batch profile update interval (hours)
ENGAGEMENT_PROFILE_UPDATE_INTERVAL = int(os.environ.get('ENGAGEMENT_PROFILE_UPDATE_INTERVAL', 6))
# Max at-risk users to scan per run
ENGAGEMENT_AT_RISK_SCAN_LIMIT = int(os.environ.get('ENGAGEMENT_AT_RISK_SCAN_LIMIT', 50))
# Min inactive days before marking user as at-risk
ENGAGEMENT_MIN_INACTIVE_DAYS = int(os.environ.get('ENGAGEMENT_MIN_INACTIVE_DAYS', 7))
