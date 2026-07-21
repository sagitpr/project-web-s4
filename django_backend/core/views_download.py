"""
Download Views — Warungio Direct App Download System

Provides:
  - /download/ — Download page with device auto-detection
  - /download/android/ — Direct APK download endpoint
  - /download/ios/ — iOS distribution (redirect or IPA download)
  - /download/api/version/ — Version info API for frontend JS
"""

import logging
import os

from django.conf import settings
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET
from django.views.generic import TemplateView

from .download_service import (
    detect_device,
    get_app_version_info,
    get_file_response,
    log_download_event,
    redirect_to_ios_distribution,
    serve_ios_manifest,
    validate_apk_integrity,
)

logger = logging.getLogger('django_backend.downloads')


class DownloadPageView(TemplateView):
    """
    Main download page at /download/.
    Renders the download page with device auto-detection via JS.
    The template uses JavaScript to refine device detection client-side
    for accuracy (iOS Safari vs desktop macOS, etc.).
    """
    template_name = 'download/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pass version info to the template
        user_agent = self.request.META.get('HTTP_USER_AGENT', '')
        detected_device = detect_device(user_agent)
        version_info = get_app_version_info()

        context.update({
            'download_enabled': settings.APP_DOWNLOAD_ENABLED,
            'detected_device': detected_device,
            'android_available': version_info['android']['available'],
            'android_version': version_info['android']['version'],
            'android_file_size': version_info['android']['file_size'],
            'ios_available': version_info['ios']['available'],
            'ios_version': version_info['ios']['version'],
            'ios_distribution_url': version_info['ios']['distribution_url'] or '',
        })
        return context


@require_GET
@never_cache
def download_android(request):
    """
    Serve the Android APK file.
    - Validates file existence
    - Computes and checks SHA256 integrity (if configured)
    - Logs download event
    - Streams the file with proper HTTP headers
    - Redirects to download page with error if unavailable (better UX than raw JSON)
    """
    if not settings.APP_DOWNLOAD_ENABLED:
        return redirect(f"{reverse('page-download')}?error=disabled")

    apk_path = settings.ANDROID_APK_PATH
    if not apk_path or not os.path.isfile(apk_path):
        logger.warning('APK file not found at: %s', apk_path)
        return redirect(f"{reverse('page-download')}?error=not_found")

    # Integrity check (only if hash is configured)
    hash_configured = bool(settings.ANDROID_APK_SHA256.strip())
    if hash_configured:
        is_valid, computed_hash = validate_apk_integrity(apk_path)
        if not is_valid:
            logger.error('APK integrity check FAILED — possible corruption or tampering')
            return redirect(f"{reverse('page-download')}?error=integrity")

    # Log the download event
    ip = request.META.get('REMOTE_ADDR', 'unknown')
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    referer = request.META.get('HTTP_REFERER', '')
    log_download_event('android', settings.ANDROID_APK_VERSION, ip, user_agent, referer)

    # Determine download filename
    download_name = f'Warungio-v{settings.ANDROID_APK_VERSION}-build{settings.ANDROID_APK_BUILD_NUMBER}.apk'

    try:
        return get_file_response(
            file_path=apk_path,
            download_name=download_name,
            content_type='application/vnd.android.package-archive',
        )
    except (FileNotFoundError, Http404):
        return redirect(f"{reverse('page-download')}?error=not_found")


@require_GET
@never_cache
def download_ios(request):
    """
    Handle iOS app download/distribution.
    - If IOS_DISTRIBUTION_URL is set → redirect there (App Store / TestFlight)
    - Else if IPA file exists → serve the IPA directly
    - Otherwise → redirect to download page with error
    """
    if not settings.APP_DOWNLOAD_ENABLED:
        return redirect(f"{reverse('page-download')}?error=disabled")

    ip = request.META.get('REMOTE_ADDR', 'unknown')
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    referer = request.META.get('HTTP_REFERER', '')

    # Log download event
    log_download_event('ios', settings.IOS_IPA_VERSION, ip, user_agent, referer)

    try:
        return redirect_to_ios_distribution()
    except Http404:
        return redirect(f"{reverse('page-download')}?error=ios_unavailable")


@require_GET
@never_cache
def download_ios_manifest(request):
    """Serve the iOS OTA enterprise manifest plist."""
    try:
        return serve_ios_manifest()
    except Http404:
        return redirect(f"{reverse('page-download')}?error=manifest_unavailable")


@require_GET
def download_version_api(request):
    """
    JSON API endpoint returning version info for both platforms.
    Used by frontend JS to:
      - Show/hide download buttons
      - Display version numbers
      - Show file sizes
      - Decide download URL
    """
    version_info = get_app_version_info()
    return JsonResponse(version_info)


@require_GET
def download_detect_api(request):
    """
    JSON API endpoint that detects the user's device from User-Agent.
    Returns device type for JS to use before deciding download action.
    """
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    device = detect_device(user_agent)
    return JsonResponse({
        'device': device,
        'download_url': {
            'android': '/download/android/',
            'ios': '/download/ios/',
        }.get(device, '/download/'),
    })
