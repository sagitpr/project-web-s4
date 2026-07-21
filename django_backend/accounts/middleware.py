"""
Custom middleware for Warungio Marketplace.

CSRF Exemption for API Routes
-------------------------------
API views authenticate via JWT Bearer tokens, which are NOT automatically sent
by browsers (unlike cookies). CSRF attacks exploit automatic cookie inclusion,
so JWT-authenticated requests are immune to CSRF by design.

This middleware exempts all /api/ routes from Django's CsrfViewMiddleware.
Session-based authentication still gets full CSRF protection via DRF's
SessionAuthentication.enforce_csrf(), which validates the CSRF token
independently when a session cookie authenticates the request.

Architecture rationale:
  - Django CsrfViewMiddleware runs on ALL POST requests by default.
  - For JWT API requests, CSRF checking is unnecessary and causes 403 errors
    when the JS environment can't read the csrftoken cookie (e.g., cross-origin,
    cookie blocked, prerendered pages, bookmark-triggered POSTs).
  - DRF's own SessionAuthentication.enforce_csrf() provides the needed CSRF
    protection for session-authenticated API requests.
  - Template views (non-API) retain full Django CSRF middleware protection.

Role-Based Routing
-------------------
Separates the Public Application (for guests, buyers, sellers) from the
Administration Application (for admins only). Enforces strict role-based
access control at the middleware level to prevent unauthorized access.

Routing rules:
  - Unauthenticated users → Public pages (/, /auth/*, /info/*, /bantuan/*)
  - Buyers → /buyer/* only, never admin or seller pages
  - Sellers → /seller/* only, never admin or buyer pages
  - Admins → /admin-panel/* only, never public pages
  - /api/* endpoints are shared and use DRF permission classes
  - /health/ is always public
"""

import logging
import time
from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect
from django.urls import resolve, Resolver404
from django.conf import settings
import re

logger = logging.getLogger('django_backend.middleware')


class CSRFExemptAPIMiddleware(MiddlewareMixin):
    """
    Exempt all /api/ routes from Django's CsrfViewMiddleware.
    CSRF protection for session-authenticated API requests is handled
    by DRF's SessionAuthentication.enforce_csrf().
    """

    def process_request(self, request):
        if request.path.startswith('/api/'):
            request.csrf_processing_done = True


class RateLimitMiddleware:
    """
    Request monitoring middleware for observability.

    Logs high-level request metrics: path, method, IP, and response status.
    In DEBUG mode, logs all requests. In production, only logs slow requests
    (>2s) to help identify performance bottlenecks on the VPS without filling
    logs with every request.

    Actual rate limiting is handled by DRF's ScopedRateThrottle classes
    (AnonRateThrottle, UserRateThrottle, ScopedRateThrottle) configured in
    settings.REST_FRAMEWORK.DEFAULT_THROTTLE_RATES, which provide per-IP
    and per-user throttling at the API view level.

    Note: This middleware does NOT implement IP-based rate limiting because:
    - DRF's throttle classes already handle this at the view level
    - Nginx (front proxy) provides additional rate limiting before requests
      reach Django
    - Implementing IP-based limiting here would duplicate DRF's functionality
      and add unnecessary overhead on every request
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only monitor API and page requests (skip static files)
        path = request.path
        if path.startswith(('/static/', '/media/', '/assets/')):
            return self.get_response(request)

        start_time = time.time()
        response = self.get_response(request)
        duration_ms = (time.time() - start_time) * 1000

        # Log slow requests (>2s) in production, all requests in debug
        if duration_ms > 2000:
            logger.warning(
                'SLOW REQUEST — %s %s | Status: %s | Duration: %.0fms | IP: %s',
                request.method, path, response.status_code, duration_ms,
                request.META.get('REMOTE_ADDR', 'unknown'),
            )
        elif settings.DEBUG and duration_ms > 500:
            logger.info(
                'REQUEST — %s %s | Status: %s | Duration: %.0fms',
                request.method, path, response.status_code, duration_ms,
            )

        return response


# ── Role-based route patterns ──
# These define which URL prefixes each role is allowed to access.
# Used by RoleBasedRedirectMiddleware to enforce routing.

# Public routes accessible to everyone (including unauthenticated)
PUBLIC_PREFIXES = (
    '/api/', '/health/', '/static/', '/media/', '/assets/',
    '/auth/', '/info/', '/bantuan/',
    '/social-callback/',
)

# Admin-only routes
ADMIN_PREFIXES = (
    '/admin-panel/', '/admin/',
)

# Buyer-only routes
BUYER_PREFIXES = (
    '/buyer/',
)

# Seller-only routes
SELLER_PREFIXES = (
    '/seller/',
)

# Public page prefixes (no login required)
PUBLIC_PAGE_PREFIXES = (
    '/auth/', '/info/', '/bantuan/',
    '/social-callback/',
)


class RoleBasedRedirectMiddleware:
    """
    Middleware that enforces role-based routing.
    
    Prevents users from accessing pages outside their role's scope.
    Redirects to the correct dashboard based on authentication state and role.
    
    Redirect rules:
    1. Root (/) → Landing page for unauthenticated, role-dashboard for authenticated
    2. Admin trying to access /buyer/ or /seller/ → /admin-panel/
    3. Buyer trying to access /seller/ or /admin-panel/ → /buyer/home/
    4. Seller trying to access /buyer/ or /admin-panel/ → /seller/dashboard/
    5. Unauthenticated trying to access protected pages → /auth/login/
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        user = request.user
        is_authenticated = user.is_authenticated

        # Skip API, static, and health endpoints
        if path.startswith(PUBLIC_PREFIXES):
            return self.get_response(request)

        # Skip if path is '/' (handled by RootView)
        if path == '/':
            return self.get_response(request)

        # ── Admin routes ──
        if path.startswith(ADMIN_PREFIXES):
            # ⚠️ CRITICAL: The admin login page MUST be exempt from the admin auth check
            # to prevent a redirect loop (middleware redirects unauthenticated users to
            # admin login, but the login page itself starts with ADMIN_PREFIXES).
            if path == '/admin-panel/login/' or path.startswith('/admin-panel/login?'):
                return self.get_response(request)

            if not is_authenticated:
                # Redirect to admin login with ?next= parameter for post-login redirect
                from urllib.parse import quote
                return redirect(f'/admin-panel/login/?next={quote(path)}')
            role = getattr(user, 'role', None)
            is_staff = user.is_staff or user.is_superuser or role == 'admin'
            if not is_staff:
                # Non-admin user trying to access admin — redirect to their dashboard
                if role == 'seller':
                    return redirect('/seller/dashboard/')
                elif role == 'buyer':
                    return redirect('/buyer/home/')
                else:
                    return redirect('/')
            return self.get_response(request)

        # ── Buyer routes ──
        if path.startswith(BUYER_PREFIXES):
            if not is_authenticated:
                return redirect(f'/auth/login/?next={path}')
            role = getattr(user, 'role', None)
            if role == 'seller':
                return redirect('/seller/dashboard/')
            if role == 'admin':
                return redirect('/admin-panel/')
            # Buyer is allowed
            return self.get_response(request)

        # ── Seller routes ──
        if path.startswith(SELLER_PREFIXES):
            if not is_authenticated:
                return redirect(f'/auth/login/?next={path}')
            role = getattr(user, 'role', None)
            if role == 'buyer':
                return redirect('/buyer/home/')
            if role == 'admin':
                return redirect('/admin-panel/')
            # Seller is allowed
            return self.get_response(request)

        return self.get_response(request)
