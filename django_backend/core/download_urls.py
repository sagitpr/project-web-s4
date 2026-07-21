"""
URL patterns for the Warungio Direct App Download System.

Endpoints:
  /download/              — Main download page (HTML)
  /download/android/      — Direct APK download
  /download/ios/          — iOS distribution (redirect or IPA)
  /download/ios/manifest/ — OTA enterprise manifest plist
  /download/api/version/  — Version info JSON API
  /download/api/detect/   — Device detection JSON API
"""

from django.urls import path
from . import views_download

urlpatterns = [
    path(
        '',
        views_download.DownloadPageView.as_view(),
        name='page-download',
    ),
    path(
        'android/',
        views_download.download_android,
        name='download-android',
    ),
    path(
        'ios/',
        views_download.download_ios,
        name='download-ios',
    ),
    path(
        'ios/manifest/',
        views_download.download_ios_manifest,
        name='download-ios-manifest',
    ),
    path(
        'api/version/',
        views_download.download_version_api,
        name='download-api-version',
    ),
    path(
        'api/detect/',
        views_download.download_detect_api,
        name='download-api-detect',
    ),
]
