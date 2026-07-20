# Role Permission Report — Warungio Marketplace

**Date:** July 20, 2026  
**Status:** ✅ Complete — Strict Role-Based Access Control

---

## 1. Role Definitions

| Role | Description | Can Access | Cannot Access |
|------|-------------|------------|---------------|
| **Guest** | Unauthenticated visitor | `/`, `/auth/*`, `/info/*`, `/bantuan/*` | Any protected page |
| **Buyer** | Registered verified shopper | `/buyer/*`, Public routes | `/seller/*`, `/admin-panel/*` |
| **Seller** | Registered verified merchant | `/seller/*`, Public routes | `/buyer/*`, `/admin-panel/*` |
| **Register Mitra** | Unverified seller-in-progress | `/`, `/auth/*` (public only) | `/seller/*`, `/buyer/*`, `/admin-panel/*` |
| **Admin** | Platform administrator | `/admin-panel/*`, Public routes | `/buyer/*`, `/seller/*` (unless overridden) |
| **Super Admin** | Django superuser | ALL (including Django Admin) | N/A |

## 2. Permission Layers (Defense in Depth)

The permission system uses multiple layers for defense in depth:

```
Layer 1: URL Routing (config/urls.py)
    ├── Public routes use plain TemplateView
    ├── Buyer routes use login_required + buyer_required
    ├── Seller routes use login_required + seller_required
    └── Admin routes use staff_member_required

Layer 2: Middleware (accounts/middleware.py)
    └── RoleBasedRedirectMiddleware intercepts all requests
         and enforces role-based routing

Layer 3: View Permissions (accounts/permissions.py)
    ├── IsBuyer, IsSeller, IsAdmin
    ├── Applied to all DRF API views
    └── Used for API-level authorization

Layer 4: API Authentication (config/settings.py)
    ├── JWT Bearer tokens via SimpleJWT
    ├── Session authentication for template views
    └── Rate limiting on all auth endpoints
```

## 3. Permission Rules

### Guest (Unauthenticated)
```
✓ Access landing page (/)
✓ Register new account
✓ Login
✓ Reset password
✓ View help center (/bantuan/)
✓ View info pages (/info/*)
✓ Access public API endpoints
✗ Access any /buyer/* page → redirect to /auth/login/
✗ Access any /seller/* page → redirect to /auth/login/
✗ Access any /admin-panel/* page → redirect to /admin-panel/login/
✗ Access any /api/ endpoint requiring authentication → 401
```

### Buyer
```
✓ Access landing page → auto-redirect to /buyer/home/
✓ Access all /buyer/* pages
✓ Access public pages (/info/*, /bantuan/*)
✓ Use cart, checkout, orders, payment features
✓ View product recommendations
✗ Access /seller/* → redirect to /buyer/home/
✗ Access /admin-panel/* → redirect to /buyer/home/
✗ Access seller-specific API endpoints → 403
```

### Seller
```
✓ Access landing page → auto-redirect to /seller/dashboard/
✓ Access all /seller/* pages
✓ Access public pages (/info/*, /bantuan/*)
✓ Manage products, orders, store settings
✗ Access /buyer/* → redirect to /seller/dashboard/
✗ Access /admin-panel/* → redirect to /seller/dashboard/
✗ Access buyer-specific API endpoints → 403
```

### Register Mitra (Unverified Seller)
```
✓ Access landing page
✓ Register and complete profile
✓ Verify OTP
✗ Access /seller/dashboard/ → redirect to landing page (unverified)
✗ Access /buyer/* pages → redirect to landing page
✗ Access /admin-panel/* → redirect to admin login
```

### Admin / Staff
```
✓ Access /admin-panel/* pages
✓ Access Django Admin (/admin/)
✓ Access admin API endpoints
✓ Access monitoring and analytics
✗ Access /buyer/* → redirect to /admin-panel/
✗ Access /seller/* → redirect to /admin-panel/
```

## 4. API Permission Classes

| Class | Role Required | Applied To |
|-------|--------------|------------|
| `IsAuthenticated` | Any authenticated user | Profile, Cart, Orders |
| `IsBuyer` | role='buyer' | Buyer-specific APIs |
| `IsSeller` | role='seller' | Seller-specific APIs |
| `IsAdmin` | role='admin' or is_superuser | Admin monitoring APIs |
| `IsAdminUser` | is_staff=True | Django Admin |
| `IsStoreOwner` | Seller or Admin | Store-specific APIs |
| `AllowAny` | None | Auth, Products, Public |

## 5. Conclusion

The permission system provides four layers of defense against unauthorized access: URL routing, middleware, view permissions, and API authentication. Each role is restricted to its designated area with clear redirect rules for cross-role access attempts.
