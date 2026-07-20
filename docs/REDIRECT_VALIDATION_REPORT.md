# Redirect Validation Report — Warungio Marketplace

**Date:** July 20, 2026  
**Status:** ✅ Complete — No Redirect Loops, Verified Flows

---

## 1. Redirect Rules (Comprehensive)

| Scenario | Source | Destination | Status |
|----------|--------|-------------|--------|
| Guest visits `/` | `/` | Landing Page (render) | ✅ |
| Buyer visits `/` | `/` | `/buyer/home/` | ✅ |
| Seller visits `/` | `/` | `/seller/dashboard/` | ✅ |
| Admin visits `/` | `/` | `/admin-panel/` | ✅ |
| Buyer visits `/auth/login/` | `/auth/login/` | Login Page (render) | ✅ |
| Admin visits `/auth/login/` | `/auth/login/` | Login Page (render — minor) | ✅ |
| Guest visits `/buyer/home/` | `/buyer/home/` | `/auth/login/?next=/buyer/home/` | ✅ |
| Seller visits `/buyer/home/` | `/buyer/home/` | `/seller/dashboard/` | ✅ |
| Admin visits `/buyer/home/` | `/buyer/home/` | `/admin-panel/` | ✅ |
| Guest visits `/seller/dashboard/` | `/seller/dashboard/` | `/auth/login/?next=/seller/dashboard/` | ✅ |
| Buyer visits `/seller/dashboard/` | `/seller/dashboard/` | `/buyer/home/` | ✅ |
| Admin visits `/seller/dashboard/` | `/seller/dashboard/` | `/admin-panel/` | ✅ |
| Guest visits `/admin-panel/` | `/admin-panel/` | `/admin-panel/login/?next=/admin-panel/` | ✅ |
| Guest visits `/admin-panel/login/` | `/admin-panel/login/` | Admin Login (render — exempted) | ✅ |
| Buyer visits `/admin-panel/` | `/admin-panel/` | `/buyer/home/` | ✅ |
| Seller visits `/admin-panel/` | `/admin-panel/` | `/seller/dashboard/` | ✅ |

## 2. Redirect Loop Prevention

The following safeguards prevent redirect loops:

| Safeguard | Location | Description |
|-----------|----------|-------------|
| Admin Login Exemption | `middleware.py` | `/admin-panel/login/` is exempted from middleware admin check |
| ?next Parameter | `middleware.py` | Prevents redirect to same page after login |
| Role Context | `decorators.py` | Each decorator knows the user's role and redirects accordingly |
| RootView Auth Check | `views.py` | RootView checks authentication before any redirect |
| Login URL Config | `settings.py` | `LOGIN_URL = '/'` ensures Django's auth system redirects properly |

## 3. Edge Cases

### Edge Case 1: Admin directly accessing admin login while already authenticated
```
Admin visits /admin-panel/login/ while authenticated
    → Middleware exempts the path (bypasses admin check)
    → Admin login page template JS detects authentication
    → JS redirects to /admin-panel/ (immediate)
    → No loop ✓
```

### Edge Case 2: Seller accessing buyer checkout page
```
Seller visits /buyer/checkout/
    → Middleware checks BUYER_PREFIXES
    → User is seller → redirect to /seller/dashboard/
    → No loop ✓
```

### Edge Case 3: Unauthenticated user accessing protected API
```
Guest calls POST /api/orders/create/
    → Middleware skips (/api/ is PUBLIC_PREFIXES)
    → DRF permission returns 401
    → Frontend auth.js handles 401 by redirecting to login
    → No loop ✓
```

### Edge Case 4: Admin after logout
```
Admin clicks logout
    → Auth.js calls POST /api/auth/logout/
    → Reads user data BEFORE clearing localStorage
    → Detects user is admin → postLogoutUrl = /admin-panel/login/
    → Clears all localStorage and cookies
    → Redirects to /admin-panel/login/ (not public landing page)
    → Admin sees admin login page immediately
    → ✓ Proper separation of admin flow
```

### Edge Case 5: Social auth callback for admin
```
Admin logs in via Google
    → Social auth callback creates/links admin account
    → JWT generated + session set
    → RootView redirects to /admin-panel/
    → Admin sees dashboard directly
    → No loop ✓
```

## 4. Validation Results

| Test | Result | Notes |
|------|--------|-------|
| Guest access to landing page | ✅ | Landing page renders |
| Buyer login redirects to dashboard | ✅ | /buyer/home/ |
| Seller login redirects to dashboard | ✅ | /seller/dashboard/ |
| Admin login redirects to admin panel | ✅ | /admin-panel/ |
| Admin bypasses landing page | ✅ | Redirected from / to /admin-panel/ |
| Unauthenticated buyer page → login | ✅ | ?next parameter preserved |
| Unauthenticated seller page → login | ✅ | ?next parameter preserved |
| Unauthenticated admin page → admin login | ✅ | ?next parameter preserved |
| Cross-role buyer→seller blocked | ✅ | Redirect to dashboard |
| Cross-role seller→buyer blocked | ✅ | Redirect to dashboard |
| Cross-role buyer→admin blocked | ✅ | Redirect to dashboard |
| Cross-role seller→admin blocked | ✅ | Redirect to dashboard |
| Admin login loop | ✅ | Prevented by path exemption |
| Buyer/seller logout → landing page | ✅ | Proper session cleanup |
| Register Mitra unverified → public flow | ✅ | Not redirected to seller dashboard |
| Password reset flow | ✅ | OTP verification + redirect to login |

## 5. Conclusion

All redirect flows have been validated and no redirect loops exist. The middleware, decorators, and view-level checks work together to ensure every user is redirected to the correct destination based on authentication state and role. The admin login page is properly exempted from the middleware to prevent redirect loops.
