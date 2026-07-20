# Routing Report — Warungio Marketplace

**Date:** July 20, 2026  
**Status:** ✅ Complete — Public & Admin Applications Separated

---

## 1. Architecture Overview

The Warungio application has been refactored into two independent entry points sharing the same backend and database:

```
┌─────────────────────────────────────────────────────┐
│                   Warungio Backend                    │
│              (Shared API + Database)                  │
├─────────────────────┬───────────────────────────────┤
│   Public Application │   Administration Application  │
│                     │                              │
│  - Landing Page (/)  │  - Admin Login (/admin-panel/)│
│  - Auth (/auth/*)    │  - Admin Dashboard            │
│  - Buyer (/buyer/*)  │  - User Management            │
│  - Seller (/seller/*)│  - Monitoring                 │
│  - Info (/info/*)    │  - Analytics                  │
│  - Help (/bantuan/*) │  - Settings                   │
│                     │                              │
│  Roles: Guest,        │  Role: Admin Only            │
│  Buyer, Seller,       │                              │
│  Register Mitra       │                              │
└─────────────────────┴───────────────────────────────┘
```

## 2. Route Classification

### Public Routes (accessible to everyone)
| Route | Purpose | Auth Required |
|-------|---------|---------------|
| `/` | Landing Page | No (auto-redirect if authenticated) |
| `/health/` | Health Check | No |
| `/auth/*` | Login, Register, OTP, Reset Password | No |
| `/info/*` | About, Contact, Blog, Policies | No |
| `/bantuan/*` | Help Center | No |
| `/social-callback/*` | Social Auth Callbacks | No |
| `/api/*` | All API endpoints | Varies (per view) |
| `/static/*`, `/media/*`, `/assets/*` | Static files | No |

### Buyer Routes (buyers only)
| Route | Purpose | Guard |
|-------|---------|-------|
| `/buyer/home/` | Buyer Dashboard | `login_required` + `buyer_required` |
| `/buyer/products/` | Product List | `login_required` + `buyer_required` |
| `/buyer/cart/` | Shopping Cart | `login_required` + `buyer_required` |
| `/buyer/checkout/` | Checkout | `login_required` + `buyer_required` |
| `/buyer/orders/` | Order History | `login_required` + `buyer_required` |
| `/buyer/favorites/` | Favorites | `login_required` + `buyer_required` |
| `/buyer/promo/` | Promotions | `login_required` + `buyer_required` |
| `/buyer/settings/` | User Settings | `login_required` + `buyer_required` |
| `/buyer/loyalty/` | Loyalty Program | `login_required` + `buyer_required` |
| `/buyer/wallet/` | Wallet | `login_required` + `buyer_required` |
| `/buyer/reviews/` | Reviews | `login_required` + `buyer_required` |
| `/buyer/profile/` | Profile | `login_required` + `buyer_required` |
| `/buyer/order-detail/` | Order Detail | `login_required` + `buyer_required` |
| `/buyer/order-success/` | Order Success | `login_required` + `buyer_required` |
| `/buyer/chat/` | Chat | `login_required` + `buyer_required` |
| `/buyer/refunds/` | Refunds | `login_required` + `buyer_required` |
| `/products/<pk>/` | Product Detail | `login_required` + `buyer_required` |

### Seller Routes (sellers only)
| Route | Purpose | Guard |
|-------|---------|-------|
| `/seller/dashboard/` | Seller Dashboard | `login_required` + `seller_required` |
| `/seller/products/` | Product Management | `login_required` + `seller_required` |
| `/seller/orders/` | Order Management | `login_required` + `seller_required` |
| `/seller/pengiriman/` | Shipping | `login_required` + `seller_required` |
| `/seller/laporan/` | Reports | `login_required` + `seller_required` |
| `/seller/keuangan/` | Finance | `login_required` + `seller_required` |
| `/seller/pelanggan/` | Customers | `login_required` + `seller_required` |
| `/seller/pengaturan/` | Settings | `login_required` + `seller_required` |
| `/seller/promo-diskon/` | Discounts | `login_required` + `seller_required` |
| `/seller/ulasan/` | Reviews | `login_required` + `seller_required` |
| `/seller/supplier/` | Suppliers | `login_required` + `seller_required` |
| `/seller/stock-prediction/` | Stock Prediction | `login_required` + `seller_required` |

### Admin Routes (administrators only)
| Route | Purpose | Guard |
|-------|---------|-------|
| `/admin-panel/login/` | Admin Login | Public (bypasses middleware) |
| `/admin-panel/` | Admin Dashboard | `staff_member_required` + middleware |
| `/admin-panel/users/` | User Management | `staff_member_required` + middleware |
| `/admin-panel/orders/` | Order Management | `staff_member_required` + middleware |
| `/admin-panel/monitoring/` | System Monitoring | `staff_member_required` + middleware |
| `/admin-panel/analytics/` | Analytics | `staff_member_required` + middleware |
| `/admin-panel/ai/` | AI Management | `staff_member_required` + middleware |
| `/admin-panel/security/` | Security | `staff_member_required` + middleware |
| `/admin-panel/settings/` | Settings | `staff_member_required` + middleware |
| `/admin/` | Django Admin | `staff_member_required` + middleware |

## 3. Entry Point Flow

```
User visits /
    ├── Unauthenticated → Landing Page (public)
    ├── Authenticated Buyer → /buyer/home/
    ├── Authenticated Seller → /seller/dashboard/
    ├── Authenticated Admin → /admin-panel/
    └── Unverified user (Register Mitra) → Landing Page (public)

Admin visits /admin-panel/
    ├── Authenticated Admin → Dashboard
    ├── Unauthenticated → /admin-panel/login/
    └── Non-admin user → Redirected to role dashboard

User visits /buyer/*
    ├── Unauthenticated → /auth/login/?next=/buyer/...
    ├── Seller → /seller/dashboard/
    ├── Admin → /admin-panel/
    └── Buyer → Allowed ✓

User visits /seller/*
    ├── Unauthenticated → /auth/login/?next=/seller/...
    ├── Buyer → /buyer/home/
    ├── Admin → /admin-panel/
    └── Seller → Allowed ✓
```

## 4. Implementation Details

- **Middleware**: `RoleBasedRedirectMiddleware` in `accounts/middleware.py`
- **Decorators**: `buyer_required`, `seller_required`, `admin_required` in `accounts/decorators.py`
- **Root View**: `RootView` in `accounts/views.py` with auto-redirect logic
- **Admin Login**: `AdminLoginView` in `accounts/views.py`, template at `admin/login/index.html`
- **Admin Login Serializer**: `AdminLoginSerializer` in `accounts/serializers_admin.py`

## 5. Conclusion

The routing architecture cleanly separates the Public Application from the Administration Application. All routes are secured with multiple layers of protection (middleware, decorators, view permissions) to prevent cross-role access.
