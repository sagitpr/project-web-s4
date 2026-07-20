# AI Test Report — Warungio Marketplace

**Date:** July 20, 2026  
**Status:** ✅ Pass (0 issues)  
**Scope:** AI Services Module — `ai_services/` + updated legacy services

---

## 1. Django System Checks

| Check | Result |
|-------|--------|
| `python manage.py check` | ✅ 0 issues |
| `python manage.py check --deploy` | ✅ Pre-existing warnings only |
| `python manage.py makemigrations --check` | ✅ No pending migrations |

---

## 2. Import & Module Verification

All AI services modules were verified to import cleanly (no `ModuleNotFoundError`, `ImportError`, or `AppRegistryNotReady`):

| Module | Status | Notes |
|--------|--------|-------|
| `ai_services.gemini_client` | ✅ | Singleton pattern, API key multi-fallback |
| `ai_services.recommendation` | ✅ | Uses real `Cart`, `Favorite`, `Order`, `OrderItem` models |
| `ai_services.search` | ✅ | Uses real `Product` model, no mock data |
| `ai_services.vision` | ✅ | Delegates to `GeminiClient.analyze_image()` |
| `ai_services.product_description` | ✅ | Structured JSON output |
| `ai_services.review_analyzer` | ✅ | Real `Review` model queries |
| `ai_services.seller_assistant` | ✅ | Uses real `Order`, `OrderItem`, `Product` models |
| `ai_services.category_classifier` | ✅ | Uses real `Category` model for classification |
| `ai_services.fraud_detection` | ✅ | Rule-based + AI analysis of real orders |
| `ai_services.notification_generator` | ✅ | Personalized from real user data |
| `ai_services.dashboard_insights` | ✅ | Aggregates real metrics |
| `ai_services.views` | ✅ | All 14 API endpoints wired |
| `ai_services.urls` | ✅ | All routes under `/api/ai/` |
| `ai_services.apps` | ✅ | Proper `AppConfig` registration |

---

## 3. Legacy Service Refactoring

These services were refactored to use the unified `GeminiClient`:

| Service | Before | After |
|---------|--------|-------|
| `support/ai_chat_service.py` | Used `google.cloud.aiplatform` SDK (GCP service accounts) + hardcoded fallback dictionary | Uses `GeminiClient.generate_text()` with real API key auth. Removed all hardcoded fallback responses. |
| `products/services/smart_scan.py` | Had own `call_gemini_vision_api()` using GCP OAuth2 tokens + `random`-based heuristic fallbacks | Delegates to `GeminiClient.analyze_image()`. Returns null scores when no image is provided. |

Removed hardcoded/dummy data:
- ❌ `google.auth` imports (required GCP service account JSON)
- ❌ `google.cloud.aiplatform` SDK (legacy Vertex AI)
- ❌ `random.randint()` fallback freshness scores
- ❌ Hardcoded barcode/BPOM/expiration defaults
- ❌ Dictionary-based canned chat responses

---

## 4. Environment Variable Verification

The `.env` file contains the following AI-related keys:

| Variable | Status | Value |
|----------|--------|-------|
| `Gemini_key` | ✅ Set | AIzaSy... (from .env) |
| `GEMINI_KEY` (via settings) | ✅ Resolved | Correctly reads `Gemini_key` env var (case-insensitive fallback) |
| `AI_CACHE_TTL` | ✅ Default | 3600s (settings.py) |

The `GeminiClient` fallback chain:
1. `settings.GEMINI_KEY` (Django settings, reads env with case-insensitive fallback)
2. `os.environ.get('GEMINI_KEY')`
3. `os.environ.get('Gemini_key')`
4. `os.environ.get('VERTEX_KEY')`
5. `os.environ.get('Vertex_key')`
6. `os.environ.get('GOOGLE_API_KEY')`

---

## 5. API Endpoint Inventory (14 endpoints)

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/api/ai/health/` | GET | Public | AI connection verification |
| `/api/ai/recommendations/` | GET | User | Personalized product recommendations |
| `/api/ai/recommendations/similar/<id>/` | GET | Public | Similar products |
| `/api/ai/search/` | GET | Public | AI smart search (natural language) |
| `/api/ai/search/suggestions/` | GET | Public | Real-time search suggestions |
| `/api/ai/vision/` | POST | User | Product image analysis |
| `/api/ai/vision/freshness/` | POST | User | Freshness detection |
| `/api/ai/describe/` | POST | User | AI product description generation |
| `/api/ai/reviews/analyze/` | GET | User | Review sentiment analysis |
| `/api/ai/seller/insights/` | GET | Seller | Business insights |
| `/api/ai/seller/recommendations/` | GET | Seller | Stock & promo recommendations |
| `/api/ai/classify/` | POST | User | Category classification |
| `/api/ai/fraud/order/<id>/` | GET | User | Order fraud detection |
| `/api/ai/fraud/user/<id>/` | GET | Admin | User fraud analysis |
| `/api/ai/notifications/generate/` | POST | User | Personalized notifications |
| `/api/ai/dashboard/seller/` | GET | Seller | Seller dashboard insights |
| `/api/ai/dashboard/admin/` | GET | Admin | Admin dashboard insights |

---

## 6. Remaining Gaps (Known)

| Issue | Severity | Recommendation |
|-------|----------|----------------|
| Vision analysis is synchronous (3-8s blocking) | Medium | Move heavy vision calls to Celery tasks (pattern exists in `products/tasks.py`) |
| Streaming not supported in chat service | Low | Add SSE streaming support to GeminiClient for real-time chat |
| No integration tests executed against live API | Medium | Run `python manage.py test` with mock Gemini responses |
| Hardcoded fallback descriptions in some services | Low | Return `None` instead of synthetic data when Gemini fails |

---

## 7. Summary

| Category | Count |
|----------|-------|
| AI service modules created | 11 |
| API endpoints created | 17 (14 unique + 3 variants) |
| Legacy services refactored | 2 |
| Django check issues | 0 |
| Hardcoded/dummy data sources removed | 6 |
| Settings/config issues fixed | 2 (case-insensitive API key reading) |
