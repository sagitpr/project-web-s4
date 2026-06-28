"""
Account middleware for Warungio Marketplace.
Rate limiting, security headers, maintenance mode.
"""

import time
from django.utils import timezone
from django.http import JsonResponse
from django.conf import settings


class RateLimitMiddleware:
    """Simple rate limiting middleware using cache."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.rate_limit_cache = {}

    def __call__(self, request):
        # Apply maintenance mode check
        if getattr(settings, 'MAINTENANCE_MODE', False):
            return JsonResponse(
                {'error': 'Sistem sedang dalam pemeliharaan. Silakan coba lagi nanti.'},
                status=503
            )

        # Rate limiting for API endpoints
        if request.path.startswith('/api/'):
            ip = self.get_client_ip(request)
            path = request.path
            now = time.time()

            # Only rate limit POST/PUT/DELETE
            if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
                key = f'{ip}:{path}'
                window = 60  # 1 minute window
                max_requests = 60  # max 60 requests per minute

                if key not in self.rate_limit_cache:
                    self.rate_limit_cache[key] = []

                # Clean old entries
                self.rate_limit_cache[key] = [
                    t for t in self.rate_limit_cache[key]
                    if now - t < window
                ]

                # Check limit
                if len(self.rate_limit_cache[key]) >= max_requests:
                    return JsonResponse(
                        {'error': 'Terlalu banyak permintaan. Silakan coba lagi nanti.'},
                        status=429,
                        headers={'Retry-After': str(window)}
                    )

                # Add current request
                self.rate_limit_cache[key].append(now)

        response = self.get_response(request)

        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        if not settings.DEBUG:
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

        return response

    def get_client_ip(self, request):
        """Get client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '127.0.0.1')
