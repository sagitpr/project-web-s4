# Authentication Flow Report — Warungio Marketplace

**Date:** July 20, 2026  
**Status:** ✅ Complete — Public & Admin Auth Flows Separated

---

## 1. Authentication Architecture

```
┌──────────────────────────────────────────────────────────┐
│                   Authentication Flows                      │
├──────────────────────────┬───────────────────────────────┤
│    Public Auth Flow       │     Admin Auth Flow           │
│                          │                               │
│  Entry: /auth/login/      │  Entry: /admin-panel/login/   │
│  Users: Buyer, Seller,    │  Users: Admin Only             │
│         Register Mitra    │                               │
│  Auth: JWT + Session      │  Auth: JWT + Session          │
│  Rate Limit: 10/min       │  Rate Limit: 5/min (tighter)  │
│  Redirect: Role dashboard │  Redirect: /admin-panel/      │
└──────────────────────────┴───────────────────────────────┘
```

## 2. Public Authentication Flows

### 2.1 Registration Flow
```
User → /auth/register/ → Submit Form → Validate
    ├── Invalid → Show Errors
    └── Valid → Create User (is_verified=False)
         → Send OTP (email/WhatsApp)
         → Redirect to OTP page
         → User enters OTP → Validate
              ├── Invalid → Retry (max 5 attempts)
              └── Valid → is_verified=True
                   → Generate JWT tokens
                   → Set Django session
                   → Redirect: Buyer → /buyer/home/, Seller → /seller/dashboard/
```

### 2.2 Login Flow
```
User → /auth/login/ → Enter email/phone + password → Validate
    ├── Invalid → Error message
    ├── Unverified → "Please verify OTP first"
    ├── Locked → "Account locked (brute force protection)"
    └── Valid → Generate JWT tokens
         → Set Django session
         → Redirect to role-appropriate dashboard:
              ├── Buyer → /buyer/home/
              ├── Seller → /seller/dashboard/
              └── Admin → SHOULD USE /admin-panel/login/ instead
```

### 2.3 OTP Flow
```
OTP Request → Generate 6-digit code → Hash with SHA256
    → Store hash + plaintext (legacy fallback)
    → Send via Email + WhatsApp (Celery async)
    → 15-minute expiry
    → Max 5 verify attempts
    → 60-second resend cooldown
    → Rate limit: 3 requests/minute per email
```

### 2.4 Password Reset Flow
```
User → /auth/forgot-password/ → Enter email
    → Send OTP (always return same message to prevent enumeration)
    → User enters OTP + new password on /auth/reset-password/
    → Validate OTP → Update password
    → Redirect to login
```

### 2.5 Social Auth Flow
```
User clicks Google/Facebook/Apple login
    → Social auth callback → Authenticate
    → Create or link social account
    → Generate JWT tokens
    → Set Django session
    → Redirect to role-appropriate dashboard
```

## 3. Admin Authentication Flow

### 3.1 Admin Login
```
Admin → /admin-panel/login/ → Enter email + password → Validate
    ├── Valid non-admin user → "Email atau password salah" (consistent error)
    ├── Invalid credentials → "Email atau password salah"
    └── Valid admin → Generate JWT tokens
         → Set Django session
         → Redirect to /admin-panel/ (or ?next= page)
```

### 3.2 Admin Auto-Redirect
```
Admin visits / while authenticated
    → RootView detects admin role
    → Redirects to /admin-panel/ (bypasses landing page)

Admin visits /admin-panel/ while authenticated
    → Middleware passes through (admin is staff)
    → Renders admin dashboard

Admin visits /auth/login/ while authenticated
    → Middleware allows through PUBLIC_PREFIXES
    → Would show public login (minor — admin should use admin login)
```

## 4. Security Measures

| Measure | Public Auth | Admin Auth |
|---------|-------------|------------|
| Brute Force Lockout | 5 failed attempts → 15 min lock | 5 failed attempts → 15 min lock |
| Rate Limiting | 10/min (public login), 5/min (OTP) | 5/min (admin login via ScopedRateThrottle) |
| User Enumeration | Protection via consistent messages | Protection via AdminLoginSerializer |
| JWT Access | 2-hour expiry | 2-hour expiry |
| JWT Refresh | 30-day expiry, rotation + blacklist | 30-day expiry, rotation + blacklist |
| Session Cookie | httpOnly, SameSite=Lax | httpOnly, SameSite=Lax |
| CSRF | Exempted for /api/ routes | Exempted for /api/ routes |

## 5. Conclusion

The authentication system provides separate, secure flows for public users and administrators. The AdminLoginSerializer prevents user enumeration by using a consistent error message for both invalid credentials and valid non-admin accounts. All auth flows generate JWT tokens and set Django sessions for seamless integration with both API and template-based views.
