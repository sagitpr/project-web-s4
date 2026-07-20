# Warungio Marketplace — API Audit Report

## Executive Summary
A comprehensive audit of all API endpoints, their authentication, authorization, and security was performed.

---

## 1. API Architecture

### 1.1 Base Structure
- All API endpoints prefixed with `/api/`
- URL configuration in `django_backend/config/urls.py`
- Each app has its own `urls.py` for endpoint definitions

### 1.2 Authentication Methods
- **JWT Bearer Token** (primary) — via `JWTAuthentication`
- **Session Authentication** (secondary) — via `SessionAuthentication`
- **No Auth** — public endpoints (register, login, OTP, forgot password)

### 1.3 Default Permissions
- `IsAuthenticatedOrReadOnly` — read access for unauthenticated, write requires auth

---

## 2. Endpoint Inventory

### 2.1 Authentication Endpoints (`/api/auth/`)
| Endpoint | Method | Auth | Rate Limit | Status |
|----------|--------|------|------------|--------|
| `/api/auth/register/` | POST | None | — | ✅ |
| `/api/auth/login/` | POST | None | 10/min (AnonRateThrottle) | ✅ |
| `/api/auth/logout/` | POST | JWT | — | ✅ |
| `/api/auth/otp/request/` | POST | None | 5/min (scope: otp) | ✅ |
| `/api/auth/otp/verify/` | POST | None | — | ✅ |
| `/api/auth/otp/resend/` | POST | None | 5/min (scope: otp) | ✅ |
| `/api/auth/forgot-password/` | POST | None | — | ✅ |
| `/api/auth/reset-password/` | POST | None | — | ✅ |
| `/api/auth/check-auth/` | GET | JWT | — | ✅ |
| `/api/auth/profile/` | GET/PATCH | JWT | — | ✅ |
| `/api/auth/change-password/` | POST | JWT | — | ✅ |
| `/api/auth/check-availability/` | POST | None | — | ✅ |
| `/api/auth/social/google/` | POST | None | — | ✅ |
| `/api/auth/social/facebook/` | POST | None | — | ✅ |
| `/api/auth/social/apple/` | POST | None | — | ✅ |

### 2.2 Store Endpoints (`/api/stores/`)
| Endpoint | Method | Auth | Status |
|----------|--------|------|--------|
| `/api/stores/` | GET | Read: None, Write: JWT | ✅ |
| `/api/stores/{id}/` | GET | Read: None | ✅ |
| `/api/stores/create/` | POST | JWT | ✅ |
| `/api/stores/my-store/` | GET/PATCH | JWT (seller) | ✅ |
| `/api/stores/{id}/follow/` | POST | JWT | ✅ |

### 2.3 Product Endpoints (`/api/products/`)
| Endpoint | Method | Auth | Status |
|----------|--------|------|--------|
| `/api/products/` | GET | None (read) | ✅ |
| `/api/products/{id}/` | GET | None (read) | ✅ |
| `/api/products/create/` | POST | JWT (seller) | ✅ |
| `/api/products/{id}/manage/` | PATCH/DELETE | JWT (seller) | ✅ |
| `/api/products/my-products/` | GET | JWT (seller) | ✅ |
| `/api/products/categories/` | GET | None | ✅ |
| `/api/products/{id}/reviews/` | GET/POST | Read: None, Write: JWT | ✅ |
| `/api/products/{id}/favorite/` | GET/POST | JWT | ✅ |
| `/api/products/recently-viewed/` | GET/POST | JWT | ✅ |
| `/api/products/check-voucher/` | POST | JWT | ✅ |
| `/api/products/search-suggestions/` | GET | None/JWT | ✅ |
| `/api/products/low-stock/` | GET | JWT (seller) | ✅ |
| `/api/products/seller-promos/` | GET/POST | JWT (seller) | ✅ |
| `/api/products/store-reviews/` | GET | JWT (seller) | ✅ |

### 2.4 Order Endpoints (`/api/orders/`)
| Endpoint | Method | Auth | Status |
|----------|--------|------|--------|
| `/api/orders/my-orders/` | GET | JWT (buyer) | ✅ |
| `/api/orders/seller/` | GET | JWT (seller) | ✅ |
| `/api/orders/{id}/` | GET | JWT | ✅ |
| `/api/orders/create/` | POST | JWT (buyer) | ✅ |
| `/api/orders/{id}/status/` | POST | JWT (seller) | ✅ |
| `/api/orders/{id}/cancel/` | POST | JWT | ✅ |
| `/api/orders/{id}/tracking/` | GET | JWT | ✅ |
| `/api/orders/cart/` | GET/POST | JWT | ✅ |
| `/api/orders/cart/{id}/` | PATCH/DELETE | JWT | ✅ |
| `/api/orders/cart/count/` | GET | JWT | ✅ |
| `/api/orders/cart/clear/` | DELETE | JWT | ✅ |
| `/api/orders/shipping-methods/` | GET | JWT | ✅ |

### 2.5 Payment Endpoints (`/api/payments/`)
| Endpoint | Method | Auth | Status |
|----------|--------|------|--------|
| `/api/payments/methods/` | GET | JWT | ✅ |
| `/api/payments/config/` | GET | JWT | ✅ |
| `/api/payments/create-snap/` | POST | JWT | ✅ |
| `/api/payments/status/{id}/` | GET | JWT | ✅ |
| `/api/payments/wallet/balance/` | GET | JWT | ✅ |
| `/api/payments/wallet/transactions/` | GET | JWT | ✅ |
| `/api/payments/wallet/topup/` | POST | JWT | ✅ |
| `/api/payments/finance/summary/` | GET | JWT (seller) | ✅ |
| `/api/payments/finance/transactions/` | GET | JWT (seller) | ✅ |
| `/api/payments/finance/bank-accounts/` | GET/POST | JWT (seller) | ✅ |

### 2.6 Additional Endpoints
| App | Endpoint Prefix | Auth | Status |
|-----|----------------|------|--------|
| Analytics | `/api/analytics/` | JWT (seller) | ✅ |
| Chat | `/api/chat/` | JWT | ✅ |
| Notifications | `/api/notifications/` | JWT | ✅ |
| Refunds | `/api/refunds/` | JWT | ✅ |
| Support | `/api/support/` | JWT | ✅ |
| Inventory | `/api/inventory/` | JWT (seller) | ✅ |
| Loyalty | `/api/loyalty/` | JWT | ✅ |
| Regions | `/api/regions/` | None | ✅ |
| Suppliers | `/api/suppliers/` | JWT | ✅ |
| Subscriptions | `/api/subscriptions/` | JWT | ✅ |
| Monitoring | `/api/monitoring/` | JWT (admin) | ✅ |

### 2.7 JWT & Utility Endpoints
| Endpoint | Method | Auth | Status |
|----------|--------|------|--------|
| `/api/token/` | POST | None | ✅ |
| `/api/token/refresh/` | POST | None | ✅ |
| `/api/token/blacklist/` | POST | JWT | ✅ |
| `/api/schema/` | GET | None | ⚠️ Swagger |
| `/api/docs/` | GET | None | ⚠️ Swagger UI |
| `/api/redoc/` | GET | None | ⚠️ Redoc |
| `/health/` | GET | None | ✅ |

### 2.8 Frontend Page Routes
| Route | Protection | Status |
|-------|-----------|--------|
| `/` | None (Landing page) | ✅ |
| `/auth/login/` | None | ✅ |
| `/auth/register/` | None | ✅ |
| `/auth/otp/` | None | ✅ |
| `/auth/reset-password/` | None | ✅ |
| `/auth/register-mitra/` | None | ✅ |
| `/buyer/*` | `login_required` | ✅ |
| `/seller/*` | `login_required` | ✅ |
| `/admin-panel/*` | `staff_member_required` | ✅ |
| `/admin/` | Django Admin auth | ✅ |

---

## 3. API Security Audit

### 3.1 Authentication & Authorization
| Check | Status | Notes |
|-------|--------|-------|
| All API endpoints require auth | ✅ | Public endpoints explicitly allowed |
| Role-based access | ✅ | buyer/seller/admin separation |
| IDOR protection | ✅ | User-scoped queries (request.user) |
| Object-level permissions | ✅ | Owner checks implemented |

### 3.2 Input Validation
| Check | Status | Notes |
|-------|--------|-------|
| DRF Serializer validation | ✅ | All endpoints use serializers |
| SQL Injection protection | ✅ | ORM-based queries |
| XSS protection | ✅ | Template escaping + DRF JSON output |
| File upload validation | ✅ | Extension + MIME type check |

### 3.3 Rate Limiting
| Scope | Rate | Applies To |
|-------|------|-----------|
| `anon` (global) | 100/hour | All unauthenticated requests |
| `user` (global) | 1000/hour | All authenticated requests |
| `otp` | 5/minute | OTP request/resend |
| `login` | 10/minute | Login attempts |

**⚠️ Limitation:** Rate limiting is only configured for OTP and login scopes. All other endpoints use the global `anon`/`user` rates. Consider adding app-specific rate limits for:
- Product creation (spam prevention)
- Order creation (fraud prevention)
- Chat messages (spam prevention)

---

## 4. API Response Format

All API responses follow a consistent JSON format:
```json
{
    "message": "Success message",
    "data": { ... },
    "error": "Error message"
}
```

Error responses include:
```json
{
    "detail": "Error description",
    "field": "field_name",
    "code": "error_code"
}
```

---

## 5. WebSocket Endpoints

| Endpoint | Protocol | Auth | Purpose |
|----------|----------|------|---------|
| `ws://host/ws/notifications/` | WebSocket | JWT Token | Real-time notifications |
| `ws://host/ws/chat/{room}/` | WebSocket | JWT Token | Real-time chat |

Both endpoints validate JWT token on connection.

---

## Summary

| Category | Status |
|----------|--------|
| Endpoint Coverage | ✅ 60+ API endpoints |
| Authentication | ✅ JWT + Session |
| Authorization | ✅ Role-based + object-level |
| Rate Limiting | ✅ Configured (can be expanded) |
| Input Validation | ✅ DRF serializers |
| CSRF Protection | ✅ Architecturally secure |
| WebSocket | ✅ JWT-authenticated |

## Recommendations
1. Add specific rate limits for order creation and chat endpoints
2. Protect Swagger/API docs behind staff authentication in production
3. Add pagination validation to prevent large offset attacks
4. Consider adding request body size limits per endpoint
