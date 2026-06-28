"""
Django settings for Warungio Marketplace.
Hybrid Django + PHP backend with MySQL, REST Framework, JWT, Channels.
"""

import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# =============================================================================
# LOAD .ENV FROM PROJECT ROOT (single source of truth)
# =============================================================================
# All backends (PHP, Node.js, Django) share the same root .env file.
# Django specific settings can be overridden via django_backend/.env

try:
    from dotenv import load_dotenv
    root_env = BASE_DIR / '.env'
    django_env = BASE_DIR / 'django_backend' / '.env'
    # Load root .env first (shared config) — override=True so .env always wins
    if root_env.exists():
        load_dotenv(root_env, override=True)
    # Then load Django-specific .env (overrides)
    if django_env.exists():
        load_dotenv(django_env, override=True)
except ImportError:
    pass  # python-dotenv not installed — rely on system env vars

# =============================================================================
# SECURITY
# =============================================================================
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-warungio-marketplace-key-change-in-production'
)
DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() == 'true'

# Production security — configurable via env vars, defaults safe for dev
SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
CSRF_COOKIE_SECURE = os.environ.get('CSRF_COOKIE_SECURE', 'False').lower() == 'true'
SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'False').lower() == 'true'
SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', '0'))
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,0.0.0.0,.run.app,.railway.app,').split(',')

# =============================================================================
# APPLICATION DEFINITION
# =============================================================================
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
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# =============================================================================
# MIDDLEWARE
# =============================================================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'accounts.middleware.RateLimitMiddleware',
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
            'PASSWORD': os.environ.get('DB_PASS', 'warungio_secret'),
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
            'PASSWORD': os.environ.get('DB_PASS', 'warungio_secret'),
            'HOST': db_host,
            'PORT': os.environ.get('DB_PORT', '3306'),
            'OPTIONS': db_options,
        }

    DATABASES = {'default': db_config}

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

# Check if Redis is available (with short timeout to avoid blocking tests)
def _get_channel_layer_config():
    try:
        import redis as _redis
        r = _redis.Redis.from_url(REDIS_URL, socket_timeout=2, socket_connect_timeout=2)
        r.ping()
        return {
            'default': {
                'BACKEND': 'channels_redis.core.RedisChannelLayer',
                'CONFIG': {
                    'hosts': [REDIS_URL],
                    'capacity': 1500,
                    'expiry': 60,
                },
            },
        }
    except Exception:
        return {
            'default': {
                'BACKEND': 'channels.layers.InMemoryChannelLayer',
            },
        }

CHANNEL_LAYERS = _get_channel_layer_config()

# =============================================================================
# CACHING
# =============================================================================
def _get_cache_config():
    try:
        import redis as _redis
        r = _redis.Redis.from_url(REDIS_URL, socket_timeout=2, socket_connect_timeout=2)
        r.ping()
        return {
            'default': {
                'BACKEND': 'django_redis.cache.RedisCache',
                'LOCATION': REDIS_URL,
                'OPTIONS': {
                    'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                },
            },
        }
    except Exception:
        return {
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
                'LOCATION': 'warungio-cache',
            },
        }

CACHES = _get_cache_config()

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

# =============================================================================
# AUTHENTICATION
# =============================================================================
AUTH_USER_MODEL = 'accounts.User'
LOGIN_URL = '/auth/login/'

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
    },
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
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
    'AUTH_HEADER_TYPES': ('Bearer', 'JWT'),
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
CORS_ALLOW_ALL_ORIGINS = DEBUG
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
    BASE_DIR / 'assets',
    BASE_DIR / 'shared',
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

FACEBOOK_APP_ID = os.environ.get('FACEBOOK_APP_ID', 'your-facebook-app-id')
FACEBOOK_APP_SECRET = os.environ.get('FACEBOOK_APP_SECRET', '')

APPLE_CLIENT_ID = os.environ.get(
    'APPLE_CLIENT_ID',
    'com.warungio.app'
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
    'AIzaSyBXr9qOQ5DfcxG-tH288SE9tpdJ5ty7S4I'  # Default dev key
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

# Provide dummy credentials when running tests to bypass _email_configured() check
import sys
if 'test' in sys.argv:
    if not EMAIL_HOST_USER:
        EMAIL_HOST_USER = 'dummy@warungio.com'
    if not EMAIL_HOST_PASSWORD:
        EMAIL_HOST_PASSWORD = 'dummy_password'
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@warungio.com')

# =============================================================================
# LOGGING
# =============================================================================

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

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
            'level': 'DEBUG' if DEBUG else 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },

        'file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'django.log',
            'maxBytes': 10 * 1024 * 1024,  # 10MB
            'backupCount': 5,
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
            'level': 'DEBUG' if DEBUG else 'INFO',
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
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https') if SESSION_COOKIE_SECURE else None

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = True
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
        {'name': 'Support', 'description': 'Tiket bantuan & support center'},
        {'name': 'Subscriptions', 'description': 'Langganan toko'},
    ],
    'SWAGGER_UI_DIST': 'SIDECAR',
    'SWAGGER_UI_FAVICON_HREF': 'SIDECAR',
    'POSTPROCESSING_HOOKS': [
        'drf_spectacular.hooks.postprocess_schema_enums',
    ],
}

# =============================================================================
# VERTEX AI — LLM for Customer Service
# =============================================================================
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
