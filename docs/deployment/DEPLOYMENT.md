# WARUNGIO MARKETPLACE — DEPLOYMENT GUIDE

Version: 1.0

Environments:
- Development
- Staging
- Production

---

# 1. DEPLOYMENT OVERVIEW

Warungio menggunakan arsitektur **Django REST API** dengan frontend vanilla HTML/CSS/JS yang di-serve oleh Django template engine.

## Current Architecture

```
Browser (HTML/CSS/JS)
       │
       ▼
   Nginx (reverse proxy, static files)
       │
       ▼
   Gunicorn + Uvicorn (Django ASGI/WSGI)
       │
       ├── MySQL / MariaDB
       ├── Redis (cache, channels, Celery broker)
       └── Cloud Storage (media uploads)
```

## Services

| Service | Technology |
|---------|-----------|
| **Backend API** | Django 4.2+, Django REST Framework |
| **WebSocket** | Django Channels + Redis |
| **Async Tasks** | Celery + Redis |
| **Database** | MySQL/MariaDB (production), SQLite (dev) |
| **Cache** | Redis |
| **Payment** | Midtrans Snap (production & sandbox) |
| **Auth** | JWT (SimpleJWT) + OTP Email + Social (Google, Facebook, Apple) |
| **Real-time** | WebSocket via Django Channels |
| **Container** | Docker + Docker Compose |

---

# 2. PREREQUISITES

## Local Development

- Python 3.11+
- MySQL or MariaDB (optional — SQLite works for dev)
- Redis (optional — falls back to in-memory)
- Docker & Docker Compose (optional)

## Production

- **Cloud Run** (recommended) or any Docker-compatible host
- **Cloud SQL** (MySQL) or managed MySQL provider
- **Redis** (Memorystore, Upstash, or any Redis provider)
- **Cloud Storage** (GCS, S3, or local volume)

---

# 3. ENVIRONMENT SETUP

## 3.1 Quick Start (Development)

```bash
# 1. Clone
git clone https://github.com/your-org/warungio.git
cd warungio

# 2. Environment
cp .env.example .env
# Edit .env with your settings

# 3. Backend setup
cd django_backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# 4. Database
python manage.py migrate

# 5. Run
python manage.py runserver 0.0.0.0:8000
```

## 3.2 Environment Variables

All configuration is via `.env` file in the project root. See `.env.example` for the full list.

Key variables:

| Variable | Description |
|----------|-------------|
| `DJANGO_SECRET_KEY` | Django secret key (generate unique for production) |
| `DJANGO_DEBUG` | Set to `False` in production |
| `USE_MYSQL` | `True` for MySQL, `False` for SQLite |
| `DB_HOST` | Database host |
| `DB_HOST_TYPE` | `tcp` or `cloud_sql` |
| `REDIS_URL` | Redis connection string |
| `MIDTRANS_SERVER_KEY` | Midtrans payment server key |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_MAPS_API_KEY` | Google Maps API key |

---

# 4. DOCKER DEPLOYMENT

```bash
# Build and start all services
docker-compose up --build

# Services:
#   - web (Django + Gunicorn/Uvicorn)
#   - nginx (reverse proxy)
#   - mysql (database)
#   - redis (cache & channels)
```

## Docker Compose Structure

```yaml
services:
  nginx:       # Reverse proxy, serves static/media
  web:         # Django ASGI (Uvicorn + Gunicorn)
  mysql:       # MySQL database
  redis:       # Cache, Channels, Celery broker
  celery:      # Async task worker
```

---

# 5. CLOUD RUN DEPLOYMENT

## 5.1 Prerequisites

```bash
# Install & authenticate gcloud
gcloud auth login
gcloud config set project your-project-id

# Enable required APIs
gcloud services enable \
  cloudrun.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  cloudscheduler.googleapis.com
```

## 5.2 Build & Deploy

```bash
# Build container
gcloud builds submit --tag gcr.io/your-project/warungio

# Deploy to Cloud Run
gcloud run deploy warungio \
  --image gcr.io/your-project/warungio \
  --region asia-southeast2 \
  --platform managed \
  --allow-unauthenticated \
  --add-cloudsql-instances your-project:asia-southeast2:warungio-db \
  --min-instances 0 \
  --max-instances 10 \
  --concurrency 80 \
  --cpu 1 \
  --memory 512Mi \
  --timeout 300 \
  --set-env-vars="DJANGO_DEBUG=False,DJANGO_SECRET_KEY=...,USE_MYSQL=True,DB_HOST_TYPE=cloud_sql,CLOUD_SQL_INSTANCE=your-project:asia-southeast2:warungio-db,DB_NAME=warungio_db,DB_USER=warungio,DB_PASS=...,REDIS_URL=redis://..."
```

## 5.3 Cloud SQL Integration

The deployment uses the **Cloud SQL Auth Proxy** via Unix socket:

1. Cloud Run `cloudrun.yaml` specifies `volumes` with CSI driver `cloudsql.cloud.google.com`
2. Django connects via `/cloudsql/PROJECT:REGION:INSTANCE` socket path
3. Set `DB_HOST_TYPE=cloud_sql` in environment

## 5.4 Secrets

Sensitive values (DB_PASS, DJANGO_SECRET_KEY, MIDTRANS_SERVER_KEY, etc.) should be stored in **Secret Manager**:

```bash
gcloud secrets create midtrans-server-key --data-file=-
# (paste value, Ctrl+D)
```

Reference in `cloudrun.yaml`:
```yaml
env:
  - name: MIDTRANS_SERVER_KEY
    valueFrom:
      secretKeyRef:
        name: midtrans-server-key
        key: latest
```

---

# 6. DATABASE MIGRATIONS

```bash
# Apply pending migrations
python manage.py migrate

# Create new migration after model changes
python manage.py makemigrations

# Show SQL for a migration
python manage.py sqlmigrate <app_name> <migration_number>
```

---

# 7. STATIC & MEDIA FILES

```bash
# Collect static files to STATIC_ROOT
python manage.py collectstatic --noinput

# For production, serve via Nginx or Cloud Storage
# Static files are collected to ./staticfiles/
```

---

# 8. HEALTH CHECK

The `/health/` endpoint returns service status:

```json
{
  "status": "ok",
  "service": "warungio",
  "database": "connected"
}
```

Configured as the **startup probe** in Cloud Run:
```yaml
startupProbe:
  httpGet:
    path: /health/
    port: 8080
  initialDelaySeconds: 5
  timeoutSeconds: 5
  periodSeconds: 10
  failureThreshold: 10
```

---

# 9. MONITORING & LOGGING

- **Cloud Logging**: Django logs are sent to stdout/stderr — automatically captured by Cloud Run
- **Cloud Monitoring**: CPU, memory, request latency, instance count
- **Error Tracking**: Sentry or similar (optional)
- **Database Logs**: Available via Cloud SQL

---

# 10. SECURITY CHECKLIST

- [ ] `DJANGO_DEBUG=False`
- [ ] `DJANGO_SECRET_KEY` = long, unique, random string
- [ ] HTTPS enabled (Cloud Run provides by default)
- [ ] `SESSION_COOKIE_SECURE=True`
- [ ] `CSRF_COOKIE_SECURE=True`
- [ ] `SECURE_SSL_REDIRECT=True`
- [ ] All API keys in Secret Manager, not env vars
- [ ] Database accessed via Cloud SQL Auth Proxy (not public IP)
- [ ] CORS whitelist restricted to known origins
- [ ] File upload validation (size, type)
- [ ] Rate limiting configured (already in DRF settings)

---

# 11. PERFORMANCE TARGETS

| Metric | Target |
|--------|--------|
| API Response | < 500ms (p95) |
| Database Query | < 200ms |
| Static File Load | < 100ms (CDN) |
| Homepage Load | < 2s |
| Availability | 99.9% |
| Cold Start | < 5s (Cloud Run) |

---

# 12. BACKUP STRATEGY

- **Database**: Daily automated backups via Cloud SQL
- **Media**: Persistent volume or GCS bucket
- **Retention**: 30 days
- **Recovery Time Objective**: < 2 hours

---

# 13. RELEASE STRATEGY

```
main  ───── Production (auto-deploy via Cloud Build)
   │
   └── develop ─── Staging
          │
          └── feature/* ─── Development
```

---

# 14. TROUBLESHOOTING

## HTTP 503 / DB Connection Error

**Cause**: Cloud SQL instance not attached to Cloud Run service.

**Fix**:
```bash
gcloud run deploy warungio \
  --add-cloudsql-instances=<PROJECT>:<REGION>:<INSTANCE>
```

## Static Files 404

**Cause**: Static files not collected or wrong path.

**Fix**:
```bash
python manage.py collectstatic --noinput
```

## WebSocket Not Connecting

**Cause**: Redis not available — falls back to InMemoryChannelLayer.

**Fix**: Ensure `REDIS_URL` is set and Redis is accessible.

---

# 15. CURRENT STATUS

✅ **Local Development** — Fully functional
✅ **Docker Compose** — Fully functional
✅ **Cloud Run + Cloud SQL** — Verified
⬜ **CI/CD Pipeline** — In progress
⬜ **Custom Domain + SSL** — Configured via Cloud Run
