# Warungio Marketplace — Production Readiness Checklist

## Pre-Deployment Verification

### Environment Configuration
- [x] `.env.example` documents ALL required environment variables
- [x] `DJANGO_SECRET_KEY` is set via environment (no hardcoded fallback dependency)
- [x] `DJANGO_DEBUG` is set to `False`
- [x] `ALLOWED_HOSTS` configured with production domains only
- [x] `CORS_ALLOWED_ORIGINS` configured with production origins
- [x] `CSRF_TRUSTED_ORIGINS` configured with production domains
- [x] Database credentials set via environment variables
- [x] Email credentials set via environment variables
- [x] Midtrans credentials set via environment variables
- [x] Social auth credentials set via environment variables
- [x] Google Maps API key set via environment variables
- [x] WhatsApp API credentials set via environment variables
- [x] Redis URL configured

### Security Configuration
- [x] `SESSION_COOKIE_SECURE=True` (HTTPS-only cookies)
- [x] `CSRF_COOKIE_SECURE=True` (HTTPS-only CSRF token)
- [x] `SECURE_SSL_REDIRECT=True` (HTTP→HTTPS)
- [x] `SECURE_HSTS_SECONDS=31536000` (1 year HSTS)
- [x] `SECURE_HSTS_INCLUDE_SUBDOMAINS=True`
- [x] `SECURE_HSTS_PRELOAD=True`
- [x] `SECURE_BROWSER_XSS_FILTER=True`
- [x] `SECURE_CONTENT_TYPE_NOSNIFF=True`
- [x] `X_FRAME_OPTIONS=DENY`
- [x] `SECURE_PROXY_SSL_HEADER` configured
- [x] Nginx security headers configured
- [x] CORS configured (not all origins)
- [x] Rate limiting configured (login, OTP, global)

### Docker/Infrastructure
- [x] Docker multi-stage build (optimized)
- [x] All services have HEALTHCHECK
- [x] All services have memory limits
- [x] Log rotation configured (max-size, max-file)
- [x] Nginx configured for static/media serving
- [x] Nginx has rate limiting for API
- [x] MariaDB configured for low memory (1GB VPS)
- [x] Redis configured with maxmemory and eviction policy
- [x] Celery configured with memory-safe settings
- [x] Cloud Run startup probe configured

### Database
- [x] Migrations checked for consistency
- [x] Database indexes on all queried fields
- [x] Connection pooling configured (CONN_MAX_AGE=60)
- [x] SQL schema dump available
- [x] Proper foreign key relationships

### Monitoring & Logging
- [ ] Centralized logging system configured
- [ ] Error tracking (Sentry/GlitchTip) configured
- [ ] Performance monitoring configured
- [ ] Uptime monitoring configured
- [ ] Backup strategy documented
- [ ] Disaster recovery plan documented

### API & Integration
- [x] All API endpoints documented
- [x] Rate limiting configured on auth endpoints
- [x] Swagger/OpenAPI available (protect in production)
- [x] Webhook endpoints secured
- [ ] Midtrans payment webhook verified
- [ ] Email delivery tested
- [ ] WhatsApp OTP delivery tested

## Deployment Steps

### 1. Pre-Deployment
- [ ] Run `python manage.py check --deploy` to verify Django deployment settings
- [ ] Run `python manage.py makemigrations --check` to verify migration consistency
- [ ] Run `python manage.py test` to run all tests
- [ ] Verify all environment variables are set
- [ ] Backup current database

### 2. Build & Deploy (Docker Compose)
```bash
# Build with BuildKit
export DOCKER_BUILDKIT=1 COMPOSE_DOCKER_CLI_BUILD=1
docker-compose build

# Verify images
docker-compose images

# Deploy
docker-compose up -d

# Verify health
docker-compose ps
curl http://localhost/health/
```

### 3. Post-Deployment
- [ ] Run `docker-compose logs` to check for errors
- [ ] Test complete user flow (register → login → browse → order → pay)
- [ ] Verify WebSocket connection (notifications, chat)
- [ ] Verify email delivery (OTP, notifications)
- [ ] Monitor resource usage (CPU, memory, disk)
- [ ] Check SSL certificate validity

### 4. Cloud Run Deployment
```bash
# Build and push to Artifact Registry
gcloud builds submit --config cloudbuild.yaml

# Deploy
gcloud run deploy warungio --region asia-southeast2

# Verify
gcloud run services list
curl https://your-service.run.app/health/
```

## Post-Production Monitoring

### Day 1
- [ ] Monitor error rates
- [ ] Monitor response times
- [ ] Check for any authentication failures
- [ ] Verify payment processing

### Week 1
- [ ] Review logs for suspicious activity
- [ ] Check database performance
- [ ] Monitor Redis memory usage
- [ ] Review Celery task completion

### Month 1
- [ ] Security audit review
- [ ] Performance optimization review
- [ ] Backup verification
- [ ] SSL certificate renewal check

## Emergency Contacts & Procedures

### Rollback Procedure
```bash
# Docker Compose
docker-compose down
git checkout <previous-tag>
docker-compose up -d --build

# Cloud Run
gcloud run deploy warungio --image <previous-image>
```

### Common Issues
| Issue | Resolution |
|-------|-----------|
| Database connection failed | Check DB_HOST, credentials, Cloud SQL proxy |
| Email not sending | Verify EMAIL_HOST_USER/PASSWORD, check SMTP settings |
| OTP not delivered | Check Celery/RabbitMQ, email logs, WhatsApp API status |
| Payment failed | Verify Midtrans server key, merchant ID |
| WebSocket not connecting | Check Redis, Channel Layer configuration |
