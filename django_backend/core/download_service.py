"""
Download Service — handles app file delivery, integrity checks, version info,
and download analytics for the Warungio direct download system.

Architecture:
  - All file paths and distribution URLs come from settings (env vars / .env).
  - Files are served via Django StreamingHttpResponse for memory efficiency.
  - SHA256 hash is computed at request time (not stored) for freshness.
  - Nginx X-Accel-Redirect is preferred in production (configured upstream).
"""

import hashlib
import logging
import os
import platform
import time
from pathlib import Path
from typing import Optional, Tuple

from django.conf import settings
from django.http import (
    FileResponse,
    Http404,
    HttpResponse,
    HttpResponseRedirect,
    JsonResponse,
    StreamingHttpResponse,
)

logger = logging.getLogger('django_backend.downloads')


# ── Device Detection ──────────────────────────────────────────────────────


def detect_device(user_agent: str) -> str:
    """
    Detect the user's device platform from the User-Agent string.
    Returns one of: 'android', 'ios', 'desktop'

    Note: This server-side detection is best-effort. The client-side JS
    refines detection using navigator.maxTouchPoints for iPadOS 13+.
    """
    ua = user_agent.lower() if user_agent else ''

    if not ua:
        return 'desktop'

    if 'android' in ua:
        return 'android'

    # iOS detection: iPhone, iPad, iPod touch
    # 'like mac os x' appears in ALL Safari UAs (macOS + iOS),
    # so we check for device-specific keywords first.
    if any(kw in ua for kw in ('iphone', 'ipad', 'ipod')):
        return 'ios'

    # iPad on iOS 13+ sometimes shows 'Macintosh' without 'iPad'.
    # For server-side, this is ambiguous (could be desktop Mac).
    # The frontend JS handles this case via navigator.maxTouchPoints.

    return 'desktop'


# ── File Validation / Integrity ────────────────────────────────────────────


def compute_sha256(file_path: str, chunk_size: int = 65536) -> str:
    """Compute SHA256 hash of a file in chunks (memory-safe for large APKs)."""
    sha = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            sha.update(chunk)
    return sha.hexdigest()


def validate_apk_integrity(file_path: str) -> Tuple[bool, Optional[str]]:
    """
    Validate APK file integrity against the configured SHA256 hash.
    Returns (is_valid, computed_hash_or_None).
    If no hash is configured, validation is skipped (returns True, None).
    """
    expected_hash = settings.ANDROID_APK_SHA256.strip()
    if not expected_hash:
        return True, None  # No hash configured — skip validation

    try:
        computed = compute_sha256(file_path)
    except (OSError, PermissionError) as e:
        logger.error('Cannot read file for hash computation: %s', e)
        return False, None

    is_valid = computed.lower() == expected_hash.lower()
    if not is_valid:
        logger.warning(
            'APK integrity mismatch: expected=%s computed=%s',
            expected_hash, computed,
        )
    return is_valid, computed


# ── Version Info API ───────────────────────────────────────────────────────


def get_app_version_info() -> dict:
    """
    Return version info for both platforms.
    This is used by the download page JS to show version/status.
    """
    apk_exists = os.path.isfile(settings.ANDROID_APK_PATH) if settings.APP_DOWNLOAD_ENABLED else False
    ios_configured = bool(settings.IOS_IPA_PATH) or bool(settings.IOS_DISTRIBUTION_URL)

    response = {
        'enabled': settings.APP_DOWNLOAD_ENABLED,
        'android': {
            'available': apk_exists,
            'version': settings.ANDROID_APK_VERSION,
            'build': settings.ANDROID_APK_BUILD_NUMBER,
            'package_name': settings.ANDROID_APK_PACKAGE_NAME,
            'file_name': Path(settings.ANDROID_APK_PATH).name if apk_exists else None,
            'file_size': os.path.getsize(settings.ANDROID_APK_PATH) if apk_exists else 0,
        },
        'ios': {
            'available': ios_configured,
            'version': settings.IOS_IPA_VERSION,
            'build': settings.IOS_IPA_BUILD_NUMBER,
            'bundle_id': settings.IOS_BUNDLE_ID,
            'distribution_url': settings.IOS_DISTRIBUTION_URL or None,
            'ipa_available': bool(settings.IOS_IPA_PATH and os.path.isfile(settings.IOS_IPA_PATH)),
        },
    }
    return response


# ── File Serving ───────────────────────────────────────────────────────────


def get_file_response(
    file_path: str,
    download_name: str,
    content_type: str = 'application/vnd.android.package-archive',
    as_attachment: bool = True,
) -> HttpResponse:
    """
    Create an appropriate HTTP response for serving the download file.
    Uses FileResponse (streaming) for efficiency with large files, or
    X-Accel-Redirect (nginx internal redirect) when USE_X_ACCEL_REDIRECT is enabled.
    Sets proper Content-Disposition, Content-Length, Cache-Control headers.
    """
    if not os.path.isfile(file_path):
        logger.error('Download file not found: %s', file_path)
        raise Http404('File tidak ditemukan')

    file_size = os.path.getsize(file_path)

    # Production mode: use nginx X-Accel-Redirect for zero-overhead file serving
    if getattr(settings, 'USE_X_ACCEL_REDIRECT', False):
        # Map the file path to the /download-files/ internal URL
        # The file is stored under django_backend/downloads/
        response = HttpResponse()
        response['X-Accel-Redirect'] = f'/download-files/{os.path.basename(file_path)}'
        response['Content-Type'] = content_type
        response['Content-Disposition'] = f'attachment; filename="{download_name}"'
        response['Content-Length'] = file_size
        response['X-Content-Type-Options'] = 'nosniff'
        return response

    # Development mode: serve directly through Django
    # Use FileResponse for efficient streaming
    response = FileResponse(
        open(file_path, 'rb'),
        as_attachment=as_attachment,
        filename=download_name,
        content_type=content_type,
    )

    # Explicit Content-Length so the browser shows accurate progress
    response['Content-Length'] = file_size

    # Cache control — APKs should not be cached long (users should get latest)
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'

    # Security headers
    response['X-Content-Type-Options'] = 'nosniff'
    response['X-Download-Options'] = 'noopen'

    # Custom header for analytics / version tracking
    response['X-App-Version'] = settings.ANDROID_APK_VERSION
    response['X-App-Build'] = settings.ANDROID_APK_BUILD_NUMBER

    return response


def serve_ios_manifest() -> HttpResponse:
    """
    Serve the iOS OTA manifest plist file for enterprise distribution.
    Falls back gracefully with an error message if unavailable.
    """
    manifest_path = settings.IOS_MANIFEST_PATH
    if not manifest_path or not os.path.isfile(manifest_path):
        raise Http404('iOS manifest tidak tersedia')

    return FileResponse(
        open(manifest_path, 'rb'),
        content_type='application/xml',
        filename='manifest.plist',
        as_attachment=True,
    )


def redirect_to_ios_distribution() -> HttpResponse:
    """
    Redirect iOS users to the configured distribution URL
    (App Store, TestFlight, or custom page).
    Falls back to a direct IPA download if available.
    """
    dist_url = settings.IOS_DISTRIBUTION_URL
    if dist_url:
        return HttpResponseRedirect(dist_url)

    # Fallback: try direct IPA download
    ipa_path = settings.IOS_IPA_PATH
    if ipa_path and os.path.isfile(ipa_path):
        return get_file_response(
            file_path=ipa_path,
            download_name=f'warungio-{settings.IOS_IPA_VERSION}.ipa',
            content_type='application/octet-stream',
        )

    raise Http404('iOS app tidak tersedia saat ini')


# ── Download Analytics ─────────────────────────────────────────────────────


def _anonymize_ip(ip: str) -> str:
    """Anonymize IP for privacy — keep only first 3 octets."""
    if not ip or ip == 'unknown':
        return 'unknown'
    parts = ip.split('.')
    if len(parts) == 4:
        return '.'.join(parts[:3]) + '.0'
    return ip


def log_download_event(
    platform_type: str,
    version: str,
    ip: str,
    user_agent: str,
    referer: str = '',
):
    """
    Log a download event for analytics purposes.
    Respects settings.DOWNLOAD_ANALYTICS_ENABLED.
    Logs go to django_backend.downloads logger — can be routed to a file
    or analytics pipeline.
    """
    if not settings.DOWNLOAD_ANALYTICS_ENABLED:
        return

    anonymized_ip = _anonymize_ip(ip)
    logger.info(
        'DOWNLOAD — Platform: %s | Version: %s | IP: %s | UA: %s | Referer: %s',
        platform_type,
        version,
        anonymized_ip,
        (user_agent or '')[:120],
        (referer or '')[:200],
    )
