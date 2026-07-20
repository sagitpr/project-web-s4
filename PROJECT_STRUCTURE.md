# Warungio Marketplace — Project Structure

## Overview
Warungio is a hyperlocal marketplace platform for daily necessities and fresh products. Built with Django REST Framework + MySQL backend, with JWT authentication, WebSocket real-time features, and Midtrans payment integration.

## Technology Stack
- **Backend:** Django 5.x + Django REST Framework + Daphne (ASGI)
- **Database:** MariaDB/MySQL (production), SQLite (development/testing)
- **Cache/Queue:** Redis (caching, Celery broker, WebSocket channel layer)
- **Async Tasks:** Celery with Redis broker
- **Authentication:** JWT (SimpleJWT) + Session + OTP + Social Auth (Google, Facebook, Apple)
- **Payments:** Midtrans Snap (credit card, bank transfer, e-wallet, QRIS)
- **Real-time:** Django Channels (WebSocket) for chat & notifications
- **Frontend:** Vanilla JS + CSS served by Django templates
- **Infrastructure:** Docker Compose (MariaDB + Redis + Django + Nginx + Celery)
- **Deployment:** Google Cloud Run + Cloud SQL + Cloud Storage

## Directory Structure

```
├── .env.example                    # Environment variables template (SINGLE SOURCE OF TRUTH)
├── .gitignore                      # Git ignore rules
├── .dockerignore                   # Docker build ignore rules
├── .gcloudignore                   # Google Cloud deploy ignore rules
├── docker-compose.yml              # Docker Compose (production)
├── docker-compose.prod.yml         # Docker Compose overrides for production (SSL)
├── Dockerfile                      # Multi-stage Docker build
├── docker-entrypoint.sh            # Container entrypoint script
├── cloudrun.yaml                   # Google Cloud Run deployment config
├── package.json                    # Node metadata (legacy)
├── requirements.txt                # Python dependencies (legacy — use django_backend/requirements.txt)
├── manage.py                       # Django management script
├── pytest.ini                      # Pytest configuration
├── README.md                       # Project README
├── PROJECT_STRUCTURE.md            # THIS FILE — project structure documentation
├── skills-lock.json                # Agent skills lock file
│
├── django_backend/                 # ★ PRIMARY DJANGO APPLICATION ★
│   ├── manage.py                   # Django management entry point
│   ├── requirements.txt            # Python dependencies
│   ├── pytest.ini                  # Pytest configuration
│   ├── conftest.py                 # Pytest fixtures
│   ├── audit_all_endpoints.py      # API endpoint audit script
│   │
│   ├── config/                     # Django project configuration
│   │   ├── settings.py             # ALL Django settings (env vars, apps, middleware, DB, etc.)
│   │   ├── urls.py                 # Root URL configuration (API routes + frontend pages)
│   │   ├── wsgi.py                 # WSGI application (gunicorn/uwsgi)
│   │   ├── asgi.py                 # ASGI application (Daphne for WebSocket)
│   │   ├── celery.py               # Celery app configuration
│   │   ├── health.py               # Health check utilities
│   │   └── __init__.py
│   │
│   ├── accounts/                   # ★ USER AUTHENTICATION & MANAGEMENT ★
│   │   ├── models.py               # User, OTP, UserSession, SocialAccount, LoginAttempt, etc.
│   │   ├── views.py                # Register, Login, Logout, OTP verify/resend, Password reset
│   │   ├── serializers.py          # All auth serializers (register, login, OTP, etc.)
│   │   ├── urls.py                 # Auth API routes (/api/auth/*)
│   │   ├── middleware.py           # CSRF exemption for API, Rate limiting
│   │   ├── backends.py             # Custom EmailBackend (email/phone auth, brute force protection)
│   │   ├── permissions.py          # Custom permission classes
│   │   ├── exceptions.py           # Custom exception handler
│   │   ├── context_processors.py   # Template context processors
│   │   ├── tasks.py                # Celery tasks (send_otp, send_whatsapp_otp)
│   │   ├── social.py               # Social auth (Google, Facebook, Apple)
│   │   ├── admin.py                # Admin interface config
│   │   ├── tests.py                # Comprehensive auth tests
│   │   ├── apps.py                 # App configuration
│   │   ├── migrations/             # Database migrations
│   │   └── services/               # Business logic services
│   │       ├── email_service.py    # Email sending
│   │       ├── whatsapp_service.py # WhatsApp OTP delivery
│   │       ├── captcha_service.py  # CAPTCHA validation
│   │       ├── notification_service.py
│   │       ├── registration_service.py
│   │       └── indonesia_validators.py
│   │
│   ├── stores/                     # ★ STORE MANAGEMENT ★
│   │   ├── models.py               # Store, StoreCategory, etc.
│   │   ├── views.py                # Store CRUD, follow/unfollow
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── tests.py
│   │   └── migrations/
│   │
│   ├── products/                   # ★ PRODUCT & CATEGORY MANAGEMENT ★
│   │   ├── models.py               # Product, Category, ProductImage, Review, Promo, etc.
│   │   ├── views.py                # Product CRUD, search, filter, reviews, promos
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── validators.py           # Product validation rules
│   │   ├── tests.py
│   │   ├── tasks.py
│   │   └── services/
│   │       ├── ai_insight.py       # AI-powered product insights
│   │       ├── smart_scan.py       # Smart Scan (barcode/OCR) service
│   │       └── stock_prediction.py # Stock prediction ML
│   │
│   ├── orders/                     # ★ ORDER & CART MANAGEMENT ★
│   │   ├── models.py               # Order, OrderItem, Cart, CartItem, Shipping, Delivery
│   │   ├── views.py                # Order CRUD, cart, checkout, tracking
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── tests.py
│   │   ├── tasks.py
│   │   └── services/
│   │       ├── binderbyte.py       # Courier tracking API client
│   │       ├── courier_tracking.py # Courier tracking service
│   │       └── distance.py         # Distance calculation
│   │
│   ├── payments/                   # ★ PAYMENT PROCESSING ★
│   │   ├── models.py               # Payment, PaymentMethod, Wallet, BankAccount, Transaction
│   │   ├── views.py                # Midtrans Snap, payment status, wallet
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── tests.py
│   │   ├── tasks.py
│   │   ├── signals.py
│   │   └── services/
│   │       ├── midtrans.py         # Midtrans API integration
│   │       └── wallet.py           # Wallet service
│   │
│   ├── analytics/                  # ★ SELLER ANALYTICS & REPORTS ★
│   │   ├── models.py               # Dashboard metrics, sales trends
│   │   ├── views.py                # Dashboard, reports, realtime analytics
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── tests.py
│   │   └── services/
│   │       └── ai_insight.py
│   │
│   ├── chat/                       # ★ BUYER-SELLER CHAT ★
│   │   ├── models.py               # Conversation, Message
│   │   ├── views.py                # Chat CRUD, WebSocket consumers
│   │   ├── consumers.py            # WebSocket consumer
│   │   ├── routing.py              # WebSocket routing
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   └── tests.py
│   │
│   ├── notifications/              # ★ PUSH NOTIFICATIONS ★
│   │   ├── models.py               # Notification
│   │   ├── views.py                # Notification CRUD, WebSocket
│   │   ├── consumers.py            # WebSocket consumer
│   │   ├── routing.py
│   │   ├── services.py
│   │   ├── signals.py              # Auto-create notifications on events
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   └── tests.py
│   │
│   ├── support/                    # ★ CUSTOMER SUPPORT & HELP CENTER ★
│   │   ├── models.py               # Ticket, FAQ, HelpArticle
│   │   ├── views.py                # Support tickets, AI chat
│   │   ├── consumers.py
│   │   ├── routing.py
│   │   ├── ai_chat_service.py      # AI-powered support chat
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── page_urls.py            # Help center page routes
│   │   ├── page_views.py
│   │   ├── admin.py
│   │   └── tests.py
│   │
│   ├── refunds/                    # ★ REFUND MANAGEMENT ★
│   │   ├── models.py               # Refund, RefundItem
│   │   ├── views.py                # Refund CRUD
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   └── admin.py
│   │
│   ├── inventory/                  # ★ INVENTORY MANAGEMENT & AI SCAN ★
│   │   ├── models.py               # Inventory, AIScanSession, AIDetectedItem
│   │   ├── views.py                # Inventory CRUD, AI scan
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── tests.py
│   │   ├── tasks.py
│   │   └── services/
│   │       ├── barcode_lookup.py
│   │       ├── expiry_service.py
│   │       └── fefo_engine.py
│   │
│   ├── loyalty/                    # ★ LOYALTY & REWARDS PROGRAM ★
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   └── admin.py
│   │
│   ├── regions/                    # ★ INDONESIAN REGIONAL DATA ★
│   │   ├── models.py               # Province, Regency, District, Village
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── tests.py
│   │   └── data/                   # Static regional data
│   │
│   ├── suppliers/                  # ★ SUPPLIER MANAGEMENT ★
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   └── admin.py
│   │
│   ├── subscriptions/              # ★ STORE SUBSCRIPTIONS ★
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   └── admin.py
│   │
│   ├── monitoring/                 # ★ SYSTEM MONITORING ★
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   └── admin.py
│   │
│   ├── core/                       # ★ CORE UTILITIES ★
│   │   ├── apps.py
│   │   └── management/commands/    # Custom management commands
│   │
│   ├── db/                         # ★ CUSTOM DATABASE BACKENDS ★
│   │   └── backends/mysql_compat/  # MySQL compatibility backend
│   │
│   ├── static/                     # ★ STATIC FILES (CSS, JS) ★
│   │   ├── css/
│   │   │   ├── style.css           # Main stylesheet
│   │   │   ├── landing.css         # Landing page styles
│   │   │   ├── premium.css         # Premium theme
│   │   │   ├── tokens.css          # Design tokens
│   │   │   ├── components.css      # Component styles
│   │   │   ├── responsive.css      # Responsive styles
│   │   │   └── pages/              # Page-specific CSS
│   │   ├── js/
│   │   │   ├── auth.js             # Authentication library (WarungioAuth)
│   │   │   ├── api.js              # API client library (WarungioAPI)
│   │   │   ├── landing.js          # Landing page JS
│   │   │   ├── nav.js              # Navigation
│   │   │   ├── script.js           # Main JS
│   │   │   ├── device-detector.js  # Device detection
│   │   │   ├── pwa-register.js     # PWA registration
│   │   │   ├── websocket.js        # WebSocket client
│   │   │   └── pages/              # Page-specific JS
│   │   │   └── utils/              # Utility JS modules
│   │   └── (compiled/minified assets)
│   │
│   └── templates/                  # ★ DJANGO TEMPLATES ★
│       ├── base.html               # Base template
│       ├── index.html              # Root index
│       ├── landing/                # Landing page
│       ├── auth/                   # Auth pages (login, register, OTP, reset password)
│       ├── buyer/                  # Buyer dashboard pages
│       ├── seller/                 # Seller dashboard pages
│       ├── admin/                  # Admin panel pages
│       ├── pages/                  # Info pages (about, contact, blog, etc.)
│       ├── components/             # Reusable components (sidebar, topbar)
│       └── email/                  # Email templates
│
├── auth/                           # ★ STANDALONE AUTH HTML PAGES ★
│   ├── login/                      # Login page (HTML + JS + CSS)
│   ├── register/                   # Registration page
│   ├── register-mitra/             # Seller registration page
│   ├── otp/                        # OTP verification page
│   ├── reset-password/             # Password reset page
│   └── callback/                   # Social auth callback
│
├── buyer/                          # ★ STANDALONE BUYER HTML PAGES ★
│   ├── cart/                       # Shopping cart
│   ├── checkout/                   # Checkout flow
│   ├── dashboard/                  # Buyer dashboard
│   ├── orders/                     # Order history
│   ├── order-detail/               # Order detail view
│   ├── order-success/              # Order success page
│   └── profile/                    # Buyer profile
│
├── seller/                         # ★ STANDALONE SELLER HTML PAGES ★
│   ├── dashboard/                  # Seller dashboard
│   ├── orders/                     # Seller orders
│   ├── order-detail/               # Order detail view
│   ├── products/                   # Product management
│   ├── reviews/                    # Review management
│   └── partner-guide/              # Partner guide
│
├── src/                            # ★ MODULAR FRONTEND SOURCE ★
│   ├── services/
│   │   ├── api.js                  # API client
│   │   └── websocket.js            # WebSocket client
│   └── utils/
│       ├── auth.js                 # Auth utilities
│       └── notifications.js        # Notification UI
│
├── backend/                        # ★ LEGACY PHP BACKEND (DEPRECATED) ★
│   ├── config/
│   │   └── api_keys.php            # API keys config (reads from .env)
│   └── legacy/                     # Legacy PHP endpoints (no longer used)
│       ├── config/                 # Legacy config files
│       ├── api.php                 # Legacy API
│       ├── register.php            # Legacy registration
│       ├── login.php               # Legacy login
│       └── ...                     # (Other legacy PHP files)
│
├── assets/                         # ★ STATIC ASSETS ★
│   └── pwa/                        # PWA manifest and service worker
│
├── nginx/                          # ★ NGINX CONFIGURATION ★
│   ├── nginx.conf                  # Main nginx config
│   ├── default.conf                # Default server config
│   ├── nginx.dev.conf              # Development config
│   └── warungio.conf               # Production SSL config
│
├── mariadb/                        # ★ MARIADB CONFIGURATION ★
│   └── conf.d/low-memory.cnf       # Low-memory MariaDB config (1GB VPS)
│
├── database/                       # ★ DATABASE SCHEMAS ★
│   ├── GUIDE.md                    # Database guide
│   ├── warungio_full_schema.sql    # Full database schema dump
│   └── schema/                     # Individual migration SQL files
│
├── docs/                           # ★ DOCUMENTATION ★
│   ├── architecture.md             # Architecture overview
│   ├── deployment.md               # Deployment guide
│   ├── Task_Roadmap.md             # Development roadmap
│   ├── AUDIT_CLEANUP_REPORT.md     # Previous audit cleanup report
│   ├── api/FLUTTER_API_CONTRACT.md # Flutter API contract
│   ├── architecture/ARCHITECTURE.md
│   ├── database/Database.md
│   └── deployment/DEPLOYMENT.md
│
├── scripts/                        # ★ UTILITY & TEST SCRIPTS ★
│   ├── deploy.sh                   # Deployment script
│   ├── setup-vps.sh                # VPS setup script
│   ├── setup-swap.sh               # Swap file setup
│   ├── create_redirects.py         # URL redirect creation
│   ├── database_audit.py           # Database audit
│   ├── fix_paths.py                # Path fixing utility
│   ├── fix_static_tags.py          # Static tag fixing
│   ├── test_business_flow.py       # Business flow tests
│   ├── test_business_flow_http.py
│   ├── test_business_flow_orm.py
│   ├── test_buyer_full_flow.py     # Buyer E2E flow test
│   ├── test_e2e_full_flow.py       # Full E2E test
│   ├── test_midtrans_e2e.py        # Midtrans sandbox E2E
│   └── test_seller_offline*.py     # Seller offline tests
│
├── reports/                        # ★ AUDIT REPORTS ★
│   ├── index.html                  # Reports index
│   ├── audit-report.md             # Previous audit report
│   ├── fixes-applied-report.md     # Previous fixes report
│   ├── production-audit-report.html
│   └── architecture-review-buyer-ui.html
│
├── tools/                          # ★ DEVELOPMENT TOOLS ★
│   ├── check_builds.py
│   ├── check_logs.py
│   ├── cleanup_assets.py
│   ├── find_large_django.py
│   ├── fix_assets.py
│   └── _fix_login.py
│
├── home/                           # ★ LEGACY HOME PAGE ★
│   ├── index.html
│   ├── index.php
│   ├── script.js
│   └── style.css
│
├── shared/                         # ★ SHARED FRONTEND ASSETS ★
│   ├── scripts/device-detector.js
│   └── styles/responsive.css
│
├── reports/                        # ★ GENERATED HTML REPORTS ★
│   └── ...
│
├── reports/style.css               # Reports stylesheet
├── reports/script.js               # Reports JS
│
├── stitch_assets/                  # ★ AI ARTIFACTS (SAFE TO REMOVE) ★
│   ├── code.txt
│   └── screen.html
│
├── stitch_assets_download.py       # AI artifact downloader
├── install.ps1                     # Windows install script
├── powershell.bat                  # PowerShell launcher
├── print_settings.py               # Print Django settings
├── eval_settings.py                # Settings evaluation
└── .agent/                         # Agent configuration (skills, AI tools)
    └── skills/                     # Installed AI agent skills
