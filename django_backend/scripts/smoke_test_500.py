"""
HTTP 500 Smoke Test — Warungio Endpoint Validation (Expanded)
Covers 30+ endpoints across all modules.
"""
import os, sys

_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_current_dir)
sys.path.insert(0, _project_root)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ['DJANGO_DEBUG'] = 'True'

import django
django.setup()

from django.conf import settings
settings.ALLOWED_HOSTS.append('testserver')

from django.test import Client
from django.urls import resolve, Resolver404

client = Client(HTTP_HOST='testserver')

ENDPOINTS = [
    # Health & Root
    ('GET', '/health/', {}),
    # Auth
    ('GET', '/api/auth/login/', {}),
    # Stores
    ('GET', '/api/stores/', {}),
    ('GET', '/api/stores/categories/', {}),
    ('GET', '/api/stores/my-store/', {}),
    ('GET', '/api/stores/my-followed/', {}),
    # Products
    ('GET', '/api/products/', {}),
    ('GET', '/api/products/featured/', {}),
    ('GET', '/api/products/categories/', {}),
    ('GET', '/api/products/my-products/', {}),
    ('GET', '/api/products/my-favorites/', {}),
    ('GET', '/api/products/recently-viewed/', {}),
    ('GET', '/api/products/search-suggestions/', {}),
    ('GET', '/api/products/low-stock/', {}),
    ('GET', '/api/products/stock-prediction/', {}),
    ('GET', '/api/products/promos/', {}),
    ('GET', '/api/products/seller-promos/', {}),
    ('GET', '/api/products/reviews/mine/', {}),
    ('GET', '/api/products/store-reviews/', {}),
    # Orders
    ('GET', '/api/orders/cart/', {}),
    ('GET', '/api/orders/cart/count/', {}),
    ('GET', '/api/orders/my-orders/', {}),
    ('GET', '/api/orders/history/', {}),
    ('GET', '/api/orders/shipping-methods/', {}),
    ('GET', '/api/orders/offline-sales/', {}),
    ('GET', '/api/orders/delivery/rate/', {}),
    # Payments
    ('GET', '/api/payments/methods/', {}),
    ('GET', '/api/payments/config/', {}),
    ('GET', '/api/payments/config/public/', {}),
    ('GET', '/api/payments/wallet/balance/', {}),
    ('GET', '/api/payments/wallet/transactions/', {}),
    ('GET', '/api/payments/history/', {}),
    ('GET', '/api/payments/merchant-status/', {}),
    ('GET', '/api/payments/finance/summary/', {}),
    ('GET', '/api/payments/finance/transactions/', {}),
    ('GET', '/api/payments/finance/bank-accounts/', {}),
    # Chat
    ('GET', '/api/chat/conversations/', {}),
    ('GET', '/api/chat/unread-count/', {}),
    # Notifications
    ('GET', '/api/notifications/', {}),
    ('GET', '/api/notifications/unread-count/', {}),
    ('GET', '/api/notifications/preferences/', {}),
    # Regions
    ('GET', '/api/regions/', {}),
    # Analytics
    ('GET', '/api/analytics/', {}),
]

def safe(s):
    return s.encode('ascii', errors='replace').decode('ascii')

def fmt_status(status):
    if status == 200:
        return 'OK'
    if status == 401:
        return 'UNAUTHORIZED'
    if status == 403:
        return 'FORBIDDEN'
    if status == 404:
        return 'NOT FOUND'
    if status == 405:
        return 'METHOD NOT ALLOWED'
    return str(status)

print('=' * 60)
print('SMOKE TEST: HTTP 500 Validation (Expanded)')
print(f'Testing {len(ENDPOINTS)} endpoints...')
print('=' * 60)

passed = 0
failed = 0

for method, url, data in ENDPOINTS:
    # Check if route exists
    try:
        resolve(url)
    except Resolver404:
        print(safe(f'  [?] {fmt_status(404):16s} {method} {url}'))
        passed += 1  # 404 is routing, not server error
        continue

    try:
        if method == 'GET':
            response = client.get(url, HTTP_ACCEPT='application/json')
        elif method == 'POST':
            response = client.post(url, data, content_type='application/json', HTTP_ACCEPT='application/json')
        else:
            response = client.generic(method, url, **{'HTTP_ACCEPT': 'application/json'})

        status = response.status_code
        if status == 500:
            print(safe(f'  [!!!] HTTP 500 ERROR        {method} {url}'))
            failed += 1
        elif status >= 400:
            print(safe(f'  [-]  {fmt_status(status):16s} {method} {url}'))
            passed += 1
        else:
            print(safe(f'  [+]  {fmt_status(status):16s} {method} {url}'))
            passed += 1
    except Exception as e:
        print(safe(f'  [!!!] EXCEPTION             {method} {url} - {e}'))
        failed += 1

print()
print('=' * 60)
if failed == 0:
    print(f'[PASS] {passed} endpoints tested — NO HTTP 500 ERRORS')
else:
    print(f'[FAIL] {passed} passed, {failed} FAILED')
print('=' * 60)
sys.exit(0 if failed == 0 else 1)
