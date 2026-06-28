"""
Health check view for Cloud Run startup probe.
Returns HTTP 200 without requiring database access, so Cloud Run
can verify the container is listening even during initial boot.
"""

from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def health_check(request):
    """Simple liveness check — responds even if DB isn't ready yet."""
    return JsonResponse({"status": "ok", "service": "warungio"})
