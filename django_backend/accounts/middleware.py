"""
Account middleware for Warungio Marketplace.
Rate limiting (cache-backed), security headers, maintenance mode.
"""

import time
from django.core.cache import cache
from django.http import JsonResponse
from django.conf import settings


class RateLimitMiddleware:
    """Rate limiting middleware using django cache framework.
    
    Uses cache (Redis or LocMemCache) instead of in-memory dict so limits
    persist across worker restarts and work in multi-process deployments.
    
    Rate limit: 60 POST/PUT/PATCH/DELETE requests per minute per IP+path.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Apply maintenance mode check
        if getattr(settings, 'MAINTENANCE_MODE', False):
            return JsonResponse(
                {'error': 'Sistem sedang dalam pemeliharaan. Silakan coba lagi nanti.'},
                status=503
            )

        # Rate limiting for API endpoints
        if request.path.startswith('/api/'):
            if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
                ip = self.get_client_ip(request)
                window = 60
                max_requests = 60
                cache_key = f'ratelimit:{ip}:{request.path}'

                # Atomic rate limit counter with expiry
                try:
                    # cache.add() is atomic: returns True if key was created, False if exists
                    added = cache.add(cache_key, 1, window)
                    if added:
                        count = 1
                    else:
                        count = cache.incr(cache_key)

                    if count > max_requests:
                        return JsonResponse(
                            {'error': 'Terlalu banyak permintaan. Silakan coba lagi nanti.'},
                            status=429,
                            headers={'Retry-After': str(window)}
                        )
                except Exception:
                    pass  # If cache fails, let request through

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
