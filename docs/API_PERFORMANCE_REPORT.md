# API Performance Report — Warungio Marketplace

**Date:** July 20, 2026

---

## 1. API Response Time Estimates

| Endpoint Category | Avg Response | P95 Response | Bottleneck |
|------------------|-------------|-------------|------------|
| Auth (login/register) | 200-500ms | 1.5s | Password hashing |
| Product list (paginated) | 50-200ms | 500ms | DB query + serialization |
| Product detail | 20-100ms | 300ms | Single lookup + related data |
| Cart operations | 30-100ms | 250ms | Simple CRUD |
| Order creation | 500ms-3s | 5s | Transaction + Midtrans API |
| Order history | 50-200ms | 500ms | Filtered + paginated |
| AI text generation | 1-3s | 5s | Gemini API latency |
| AI vision analysis | 3-8s | 12s | Gemini API + image upload |
| Analytics/reports | 500ms-5s | 10s | Large aggregations |
| Health check | <10ms | 20ms | Minimal processing |

## 2. Slowest Endpoints

| Endpoint | Method | Estimated Time | Reason |
|----------|--------|---------------|--------|
| `/api/ai/vision/freshness/` | POST | 3-8s | Gemini Vision API (synchronous) |
| `/api/ai/vision/` | POST | 3-8s | Gemini Vision API (synchronous) |
| `/api/ai/describe/` | POST | 1-3s | Gemini Text API (synchronous) |
| `/api/ai/search/` | GET | 500ms-3s | Gemini API + DB query |
| `/api/analytics/reports/export/` | GET | 1-5s | Large data aggregation |
| `/api/orders/create/` | POST | 500ms-3s | Transaction + payment API call |
| `/api/payments/midtrans-notification/` | POST | 500ms-2s | Payment verification |

## 3. Rate Limiting Effectiveness

| Throttle Class | Rate | Estimation | Status |
|---------------|------|-----------|--------|
| Anonymous (anon) | 100/hour | ~1.6 req/min | ✅ Adequate for browsing |
| Authenticated (user) | 1000/hour | ~16 req/min | ✅ Adequate |
| OTP endpoint | 5/minute | Per-IP | ✅ Security measure |
| Login endpoint | 10/minute | Per-IP | ✅ Brute force protection |

## 4. Caching Effectiveness

| Cache Target | TTL | Hit Ratio (Est.) | Benefit |
|-------------|-----|-----------------|---------|
| Product categories | 15 min | High (~90%) | Rarely changes |
| AI recommendations | 60 min | Medium (~70%) | Personalized per user |
| Search suggestions | 15 min | High (~85%) | Repeated queries |
| AI descriptions | 24 hours | Medium (~60%) | Per product |
| Chat context | 5 min | Low (~30%) | Per conversation |

## 5. Recommendations

1. **Make AI vision endpoints async** — return `task_id` immediately, Celery processes in background
2. **Add Redis response caching** for product list endpoints (15 min TTL)
3. **Add database query result caching** for analytics/report endpoints
4. **Consider `gunicorn` with async workers** for CPU-bound request handling
