# 🧠 WARUNGIO MARKETPLACE — COMPREHENSIVE LOGIC AUDIT REPORT

**Date:** July 22, 2026
**Auditor:** Buffy AI (Principal DevOps Engineer / Django Architect)
**Scope:** Full-stack logic audit — no business feature changes unless bugs found

---

## 📋 EXECUTIVE SUMMARY

| Category | Status | Critical Issues | Medium Issues |
|----------|--------|----------------|---------------|
| Request Flow (Nginx→Django→Response) | ⚠️ BUG FOUND | **1** | **3** |
| Django URL Routing & Middleware | ✅ Correct | 0 | 1 |
| ASGI WebSocket Configuration | ✅ Correct | 0 | 1 |
| Authentication & Authorization | ✅ Correct | 0 | 0 |
| Celery Task Queue | ✅ Correct | 0 | 1 |
| Database Connectivity | ✅ Correct | 0 | 0 |
| Redis Connectivity | ✅ Correct | 0 | 0 |
| Static/Media File Serving | 🔴 **BUG FOUND** | **1** | 0 |
| Environment Variables | ✅ Correct | 0 | 0 |
| Docker Compose Networking | ✅ Correct | 0 | 0 |
| Health Checks | ✅ Correct | 0 | 0 |
| Monitoring | ✅ Correct | 0 | 0 |

---

## 🔴 CRITICAL BUG FOUND: Frontend Asset Serving in Production

### BUG-01: Template-referenced CSS/JS assets not served by Nginx or Django in production

**Root Cause:** The SPA-style frontend templates (in `/home/`, `/auth/`, `/buyer/`, `/seller/` directories) reference asset files using relative paths that are only accessible in development mode.

**Evidence:**

1. **Templates use relative paths** — files like `style.css` and `script.js` are referenced next to HTML templates:
   - `home/index.html`: `<link rel="stylesheet" href="style.css">`, `<script src="script.js"></script>`
   - `auth/login/index.html`: `<link rel="stylesheet" href="style.css">`, `<script src="script.js"></script>`

2. **Development mode serves these** via DEBUG-only urlpatterns:
   ```python
   if settings.DEBUG:
       urlpatterns += static('/auth/', document_root=settings.BASE_DIR)
       urlpatterns += static('/buyer/', document_root=settings.BASE_DIR)
       urlpatterns += static('/seller/', document_root=settings.BASE_DIR)
   ```

3. **Production has NO serving mechanism** — Nginx only covers `/static/`, `/media/`, `/assets/`. Paths like `/auth/login/style.css` or `/buyer/home/script.js` fall through to the `/` location → proxied to Django → Django returns 404.

**Impact:** In production (DEBUG=False), ALL frontend pages render without CSS styling or JavaScript functionality. Pages are plain HTML with no interactivity, no AJAX calls, no form validation, no navigation.

**Fix required:** Either:
- **Option A:** Add Nginx location blocks for `/auth/`, `/buyer/`, `/seller/`, `/home/` that alias to the container filesystem paths, AND add bind-mounts of these directories to the Nginx service
- **Option B:** Add these directories to `STATICFILES_DIRS` so `collectstatic` copies their assets to `/static/`, then update template references to use `/static/...` paths
- **Option C:** Add the `static()` URL patterns for production (not just DEBUG), though this is less efficient

### BUG-02: Asset path mismatches in login template

**Evidence:** `auth/login/index.html` uses:
```html
<link rel="stylesheet" href="../../staticfiles/css/responsive.css" />
<script src="../../staticfiles/js/device-detector.js"></script>
```
- Path `../../staticfiles/css/responsive.css` resolves to `/staticfiles/css/responsive.css`
- Django's `STATIC_URL` is `/static/` (not `/staticfiles/`)
- Nginx serves `/static/` (not `/staticfiles/`)
- **Result: 404 in production**

Additionally:
```html
<img src="../../assets/images/...">
```
- Resolves to `/assets/images/...`
- The `assets/` directory only contains `pwa/` — **no `images/` subdirectory**
- **Result: 404 in production**

**Impact:** Login page has broken CSS, missing social login icons, missing store badges, and broken footer images.

---

## 🟡 MEDIUM FINDINGS

### MED-01: `USE_X_ACCEL_REDIRECT` disabled by default

**File:** `django_backend/config/settings.py` line 555-556
```python
USE_X_ACCEL_REDIRECT = os.environ.get('USE_X_ACCEL_REDIRECT', 'False').lower() == 'true'
```

**Impact:** APK/IPA files are served through Django's `FileResponse` (Python streaming) instead of Nginx's X-Accel-Redirect (zero-overhead kernel-level file serving). On a 1GB VPS, streaming large files through Python wastes memory and CPU.

**Root Cause:** The env var defaults to `False`, and production `.env` doesn't set it.

**Fix:** Set `USE_X_ACCEL_REDIRECT=true` in production `.env`. Nginx already has the internal `/download-files/` location ready.

### MED-02: Analytics WebSocket routing is a no-op

**File:** `django_backend/analytics/routing.py`
```python
websocket_urlpatterns = [
    # Analytics WebSocket would be handled by NotificationConsumer
    # for real-time dashboard updates
]
```

**Impact:** Real-time analytics dashboard updates won't work. No error is raised — the empty list is valid in Channels — but no WebSocket connections can be established for analytics.

**Root Cause:** Placeholder left during development. The analytics app was planned to share the notification WebSocket but this was never implemented.

### MED-03: Celery uses single default queue for all tasks

**File:** `django_backend/config/celery.py`
All 18 periodic tasks use `'options': {'queue': 'default'}` or no queue specification, which routes to `warungio_default` (the default queue).

**Impact:** With a single worker (concurrency=1), all tasks queue up behind each other. A long-running task (e.g., engagement batch processing) blocks time-sensitive tasks (e.g., payment reconciliation).

**Severity:** LOW for current scale — the single worker processes tasks sequentially regardless of queue. Becomes MEDIUM if multiple workers are added.

### MED-04: `CSRF_COOKIE_HTTPONLY = False`

**File:** `django_backend/config/settings.py` line 787

**Impact:** JavaScript can read the CSRF token cookie. The `CSRFExemptAPIMiddleware` exempts all `/api/` routes from CSRF checking (since JWT is the primary auth), but session-authenticated admin pages still use CSRF cookies.

**Rationale:** This is the standard Django+DRF SPA pattern — intentional and documented. The JWT primary authentication means CSRF exposure is limited. Acceptable trade-off.

### MED-05: Django HEALTHCHECK proxies to server on port 8000 (not 80)

**File:** `docker-compose.yml` django healthcheck:
```yaml
test: ["CMD-SHELL", "curl -sf http://localhost:8000/health/ > /dev/null 2>&1 || exit 1"]
```

**Impact:** The healthcheck correctly probes the Django port directly (not through Nginx), so it tests Django itself, not the full stack. This is correct for the Django container's health — it should test Django, not Nginx.

**Status:** ✅ Correct — this is intentional. The Nginx container has its own healthcheck.

### MED-06: Django celery settings use `CELERY_ENABLED: "false"` on web container

**File:** `docker-compose.yml` django service:
```yaml
environment:
  CELERY_ENABLED: "false"
```

This env var is set on the Django web container but is NOT consumed anywhere in settings.py. The `CELERY_TASK_ALWAYS_EAGER = DEBUG` setting is what controls whether tasks run in-process (DEBUG=True) or via Celery (DEBUG=False).

**Impact:** None — the env var exists but has no code path that reads it. This is dead configuration.

---

## ✅ VERIFIED CORRECT — NO ISSUES

### Request Flow: Browser → Nginx → Django → Database/Redis → Response

```
Browser → HTTPS (443) → Nginx (SSL termination) → /ws/ → WebSocket upgrade → Django ASGI (Channels)
                                                      /     → proxy_pass → Gunicorn+Uvicorn → Django → DB/Redis
                                                      /static/ → alias → /app/staticfiles/ (direct, no Django)
                                                      /media/ → alias → /app/django_backend/media/ (direct, no Django)
                                                      /assets/ → alias → /app/assets/ (direct, no Django)
                                                      /health/ → proxy_pass → Django health_check view
```

**Status:** ✅ Flow is correct. Each location has the right handler.

### Django URL Routing

```
/health/        → health_check (JSON, optionally checks DB)
/admin/         → Django admin interface
/api/auth/      → accounts app (register, login, OTP, profile, social auth)
/api/stores/    → stores app
/api/products/  → products app
/api/orders/    → orders app
/api/payments/  → payments app
/api/analytics/ → analytics app
/api/chat/      → chat app
/api/notifications/ → notifications app
/api/refunds/   → refunds app
/api/support/   → support app
/api/suppliers/ → suppliers app
/api/loyalty/   → loyalty app
/api/monitoring/→ monitoring app
/api/regions/   → regions app
/api/inventory/ → inventory app
/api/ai/        → AI services
/api/engagement/→ engagement engine
/api/intelligence/ → AI intelligence
/api/token/     → JWT token endpoints
/api/schema/    → OpenAPI schema
/api/docs/      → Swagger UI
/api/redoc/     → ReDoc
/download/      → App download system
/auth/*         → Frontend auth pages (login, register, OTP, reset-password)
/buyer/*        → Buyer SPA pages (protected by login_required + buyer_required)
/seller/*       → Seller SPA pages (protected by login_required + seller_required)
/admin-panel/*  → Admin pages (protected by staff_member_required)
/info/*         → Public info pages
/bantuan/*      → Help center
/               → RootView (landing page, redirects based on auth)
```

**Status:** ✅ Correct. All apps properly registered with `/api/` prefix. Frontend pages are correctly protected with role-based decorators. Duplicate shorthand routes have 301 redirects to canonical paths.

### Middleware Chain

| Order | Middleware | Purpose | Status |
|-------|-----------|---------|--------|
| 1 | SecurityMiddleware | HTTPS redirect, HSTS, XSS filter | ✅ Correct |
| 2 | WhiteNoiseMiddleware | Static file serving | ✅ Correct |
| 3 | CorsMiddleware | CORS headers | ✅ Correct |
| 4 | SessionMiddleware | Session management | ✅ Correct |
| 5 | CommonMiddleware | URL normalization | ✅ Correct |
| 6 | CSRFExemptAPIMiddleware | Exempt /api/ from CSRF | ✅ Correct |
| 7 | CsrfViewMiddleware | CSRF protection | ✅ Correct |
| 8 | AuthenticationMiddleware | User auth | ✅ Correct |
| 9 | MessageMiddleware | Flash messages | ✅ Correct |
| 10 | XFrameOptionsMiddleware | Clickjacking protection | ✅ Correct |
| 11 | RateLimitMiddleware | Request monitoring | ✅ Correct |
| 12 | RoleBasedRedirectMiddleware | Role-based routing | ✅ Correct |

**Status:** ✅ Correctly ordered. CSRFExemptAPIMiddleware runs BEFORE CsrfViewMiddleware (as required by its comment). RateLimitMiddleware runs last (after auth) so it can log user context.

### ASGI WebSocket Routing

```
ProtocolTypeRouter {
  http → django_asgi_app (Django's ASGI handler)
  websocket → JWTAuthMiddleware → AuthMiddlewareStack → URLRouter {
    ws/chat/<id>/          → ChatConsumer
    ws/notifications/      → NotificationConsumer
    ws/support/chat/       → SupportChatConsumer
  }
}
```

**Status:** ✅ Correct. JWT auth for WebSocket falls back to session-based auth. Nginx has dedicated `/ws/` location with long timeouts and buffering disabled.

### Docker Compose Networking

All services are on the `warungio_net` bridge network:
- `mysql` → hostname: `mysql` (Django connects via `DB_HOST=mysql` or service name)
- `redis` → hostname: `redis` (Django connects via `REDIS_URL=redis://redis:6379/0`)
- `django` → hostname: `django` (Nginx connects via upstream `server django:8000`)
- `celery` → hostname: `celery` (connects to Redis broker via same REDIS_URL)
- `celery-beat` → hostname: `celery-beat` (same Redis broker)
- `nginx` → hostname: `nginx` (exposes ports 80 and 443 to host)

**Status:** ✅ Correct. All services can resolve each other by service name via Docker's embedded DNS.

### Celery Task Configuration

| Setting | Value | Status |
|---------|-------|--------|
| Broker | Redis (REDIS_URL) | ✅ Correct |
| Result Backend | Redis | ✅ Correct |
| Serialization | JSON only | ✅ Secure |
| Concurrency | 1 worker | ✅ Correct for 1 vCPU |
| Time limits | 4m soft / 5m hard | ✅ Correct |
| Task ACK mode | Late (re-deliver on crash) | ✅ Correct |
| Prefetch multiplier | 1 (fair distribution) | ✅ Correct |
| Max tasks/child | 200 (memory leak prevention) | ✅ Correct |
| Beat scheduler | PersistentScheduler (file-based) | ✅ Correct |
| Default queue | `warungio_default` | ✅ Correct |

**Status:** ✅ Correct. All Celery settings are production-appropriate.

### Django Database Configuration

| Setting | Value | Status |
|---------|-------|--------|
| Engine | MySQL (mariadb) or SQLite fallback | ✅ Correct |
| Connection age | 60 seconds | ✅ Correct (reduces handshakes) |
| Connection pool | Implicit (CONN_MAX_AGE) | ✅ Correct |
| DB auto-detection | Docker (`mysql` hostname) vs localhost | ✅ Correct |

**Status:** ✅ Correct. Database auto-detects between Docker (service name `mysql`) and local development (`127.0.0.1` for TCP). Cloud SQL via Unix socket also supported.

### Redis Configuration

| Setting | Value | Status |
|---------|-------|--------|
| Max memory | 96mb (with 128m mem_limit) | ✅ Correct |
| Eviction policy | allkeys-lru | ✅ Correct for cache/broker |
| Persistence | None (no save, no AOF) | ✅ Correct for ephemeral use |
| Channel layer | Redis (production), InMemory (dev) | ✅ Correct |
| Cache backend | Redis (production), LocMem (dev) | ✅ Correct |
| Session backend | Redis cache (production) | ✅ Correct |

**Status:** ✅ Correct. Redis serves triple duty (Channels, cache, Celery broker) with appropriate settings.

### Nginx Configuration

| Feature | Production (warungio.conf) | Development (nginx.dev.conf) |
|---------|--------------------------|---------------------------|
| SSL termination | ✅ Yes (Let's Encrypt ready) | ❌ No (HTTP only) |
| HTTP→HTTPS redirect | ✅ Yes (301) | ❌ N/A |
| HTTP/2 | ✅ Yes | ❌ No |
| Security headers | ✅ Full (HSTS, CSP, X-Frame, etc.) | ❌ Minimal |
| Rate limiting | ✅ 50r/s API, 10r/s login | ✅ 50r/s |
| Proxy cache | ✅ Active (api_cache) | ❌ Disabled |
| WebSocket support | ✅ Separate /ws/ location | ✅ Separate /ws/ location |
| Static files | ✅ Direct Nginx serving | ✅ Direct Nginx serving |
| Gzip | ✅ Level 2 | ✅ Level 2 |

**Status:** ✅ Correct — warungio.conf is production-ready. nginx.dev.conf is appropriate for local development.

### Docker Security

| Feature | Status |
|---------|--------|
| `no-new-privileges:true` | ✅ Applied to all services |
| `cap_drop: ALL` | ✅ Applied to all services |
| `cap_add: NET_BIND_SERVICE` (nginx only) | ✅ Correct (needs port binding) |
| Read-only root filesystem | ❌ Not configured |
| Security-opt seccomp | ❌ Default profile |
| User namespace remapping | ❌ Not configured |

**Status:** ✅ Good baseline security. Read-only rootfs and custom seccomp are nice-to-haves.

### Load Order / Dependency Chain

```
Startup:
  1. mysql ──────┐
  2. redis ──────┤
                  ▼
  3. django ─────┤ (waits for mysql + redis healthy)
                  ▼
  4. nginx ──────┤ (waits for django healthy)
  5. celery ─────┤ (waits for mysql + redis + django healthy)
  6. celery-beat ┤ (waits for mysql + redis healthy)
  7. prometheus ─┤ (no dependencies)
  8. node_exporter ┤ (no dependencies)
  9. cadvisor ───┤ (no dependencies)
```

**Status:** ✅ Correct. Dependencies follow the logical startup order. Celery waits for Django to be healthy before starting (important for task registry).

### Healthcheck Chain

```
Docker HEALTHCHECK (every 30s):
  mysql      → mysqladmin ping localhost
  redis      → redis-cli ping
  django     → curl http://localhost:8000/health/
  celery     → pgrep celery.*worker
  celery-beat → pgrep celery.*beat
  nginx      → pgrep nginx
  prometheus → (none)
  node_exporter → (none)
  cadvisor   → (none)
```

**Status:** ⚠️ Prometheus, node_exporter, and cadvisor lack healthchecks. They don't crash often, but having healthchecks would improve observability.

---

## 📊 OVERALL SYSTEM HEALTH

| Component | Status | Notes |
|-----------|--------|-------|
| Request flow | ⚠️ **BUG** | Frontend CSS/JS not served in production |
| Django routing | ✅ **PASS** | All apps registered, correct prefixes |
| Middleware | ✅ **PASS** | Correct ordering with CSRF exemption |
| Authentication | ✅ **PASS** | JWT + session dual auth, account lockout |
| WebSocket | ✅ **PASS** | JWT auth upgrade, proper Nginx handling |
| Celery | ✅ **PASS** | All settings correct, beat separated |
| Database | ✅ **PASS** | MySQL auto-config, 60s connection age |
| Redis | ✅ **PASS** | Triple role, proper memory limits |
| Nginx | ✅ **PASS** | Production configuration complete |
| Docker Compose | ✅ **PASS** | All networks, volumes, dependencies correct |
| Environment vars | ✅ **PASS** | Sensible defaults, .env file support |
| Health checks | ⚠️ **OK** | Monitoring containers lack healthchecks |
| Monitoring | ✅ **PASS** | Prometheus + cadvisor + node_exporter |
| SSL/TLS | ⚠️ **Certs missing** | Config ready, certs need generation |

---

## 🏁 CONCLUSION

The Warungio marketplace system is **logically correct** with **one critical production bug** and several medium issues.

**CRITICAL (must fix before going live):**
1. Frontend CSS/JS assets not served in production — all SPA pages render without styling or interactivity
2. Auth login template references incorrect asset paths (`staticfiles/` vs `static/`, missing `assets/images/`)

**MEDIUM (should fix before launch):**
1. Enable `USE_X_ACCEL_REDIRECT=true` in production for efficient APK downloads
2. Analytics WebSocket routing is a placeholder — real-time dashboards won't connect
3. Celery single queue may block time-sensitive tasks under load

**All other systems verified correct:**
- ✅ Request flow: Browser → Nginx → Django → DB/Redis → Response
- ✅ WebSocket flow: Browser → Nginx → Django ASGI (Channels)
- ✅ Celery flow: Beat → Redis → Worker → DB
- ✅ Authentication flow: Login → JWT → Bearer token → Protected endpoints
- ✅ Docker Compose networking and service dependencies
- ✅ Middleware chain ordering
- ✅ Database and Redis connectivity
- ✅ Startup script and health check logic
