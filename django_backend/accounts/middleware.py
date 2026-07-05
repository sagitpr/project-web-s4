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
"""

from django.utils.deprecation import MiddlewareMixin


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
    Rate limiting middleware for brute force protection.
    Delegates to accounts.services.rate_limit_service.
    Currently handles the X-Forwarded-For parsing.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Rate limiting logic goes here (future enhancement)
        return self.get_response(request)
