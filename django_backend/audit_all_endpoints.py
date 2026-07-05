"""
Warungio Production Readiness Audit — Full Endpoint Crawler
Tests every known endpoint with correct HTTP methods, captures errors.
"""
import os, sys, json, urllib.request, urllib.error, http.cookiejar, re, traceback

BASE = 'http://localhost:8000'

# ── All known endpoints from config/urls.py and all app urls.py ──
ENDPOINTS = [
    # Health
    ('/health/', 'GET', 'health-check'),

    # Auth API
    ('/api/auth/register/', 'POST', '{"email":"audit@test.com","password":"Test1234!","password2":"Test1234!","full_name":"Audit Test","phone":"08123450001"}'),
    ('/api/auth/login/', 'POST', '{"email":"audit@test.com","password":"wrong"}'),
    ('/api/auth/logout/', 'POST', '{}'),
    ('/api/auth/check-auth/', 'GET', None),
    ('/api/auth/token-refresh/', 'POST', '{}'),
    ('/api/auth/profile/', 'GET', None),
    ('/api/auth/change-password/', 'POST', '{}'),
    ('/api/auth/otp/request/', 'POST', '{"email":"audit@test.com","purpose":"registration"}'),
    ('/api/auth/otp/verify/', 'POST', '{"email":"audit@test.com","otp_code":"123456","purpose":"registration"}'),
    ('/api/auth/otp/resend/', 'POST', '{"email":"audit@test.com","purpose":"registration"}'),
    ('/api/auth/forgot-password/', 'POST', '{"email":"audit@test.com"}'),
    ('/api/auth/reset-password/', 'POST', '{"email":"audit@test.com","otp_code":"123456","new_password":"Test1234!","new_password2":"Test1234!"}'),
    ('/api/auth/social/google/', 'POST', '{}'),
    ('/api/auth/social/facebook/', 'POST', '{}'),
    ('/api/auth/social/apple/', 'POST', '{}'),
    ('/api/auth/social/accounts/', 'GET', None),

    # JWT
    ('/api/token/', 'POST', '{"email":"audit@test.com","password":"wrong"}'),
    ('/api/token/refresh/', 'POST', '{"refresh":"dummy"}'),
    ('/api/token/blacklist/', 'POST', '{"refresh":"dummy"}'),

    # Products
    ('/api/products/', 'GET', None),
    ('/api/products/categories/', 'GET', None),
    ('/api/products/my-products/', 'GET', None),
    ('/api/products/create/', 'POST', '{}'),
    ('/api/products/1/', 'GET', None),
    ('/api/products/1/manage/', 'GET', None),
    ('/api/products/1/reviews/', 'GET', None),
    ('/api/products/1/favorite/', 'GET', None),
    ('/api/products/1/quality-checks/', 'GET', None),
    ('/api/products/reviews/mine/', 'GET', None),
    ('/api/products/store-reviews/', 'GET', None),
    ('/api/products/seller-promos/', 'GET', None),
    ('/api/products/low-stock/', 'GET', None),
    ('/api/products/recently-viewed/', 'GET', None),
    ('/api/products/search-suggestions/', 'GET', None),
    ('/api/products/check-voucher/', 'POST', '{}'),

    # Stores
    ('/api/stores/', 'GET', None),
    ('/api/stores/1/', 'GET', None),
    ('/api/stores/create/', 'POST', '{}'),
    ('/api/stores/my-store/', 'GET', None),
    ('/api/stores/my-followed/', 'GET', None),
    ('/api/stores/1/follow/', 'GET', None),

    # Orders
    ('/api/orders/cart/', 'GET', None),
    ('/api/orders/cart/count/', 'GET', None),
    ('/api/orders/shipping-methods/', 'GET', None),
    ('/api/orders/my-orders/', 'GET', None),
    ('/api/orders/seller/', 'GET', None),
    ('/api/orders/1/', 'GET', None),
    ('/api/orders/1/tracking/', 'GET', None),

    # Payments
    ('/api/payments/methods/', 'GET', None),
    ('/api/payments/config/', 'GET', None),
    ('/api/payments/wallet/balance/', 'GET', None),
    ('/api/payments/wallet/transactions/', 'GET', None),

    # Analytics
    ('/api/analytics/dashboard/', 'GET', None),
    ('/api/analytics/sales/', 'GET', None),
    ('/api/analytics/reports/', 'GET', None),

    # Regions
    ('/api/regions/provinces/', 'GET', None),
    ('/api/regions/provinces/31/', 'GET', None),
    ('/api/regions/regencies/?province=31', 'GET', None),
    ('/api/regions/regencies/3171/', 'GET', None),
    ('/api/regions/districts/?regency=3171', 'GET', None),
    ('/api/regions/districts/317101/', 'GET', None),
    ('/api/regions/villages/?district=317101', 'GET', None),
    ('/api/regions/villages/3171010001/', 'GET', None),
    ('/api/regions/search/', 'GET', None),

    # Chat
    ('/api/chat/conversations/', 'GET', None),
    ('/api/chat/unread-count/', 'GET', None),

    # Notifications
    ('/api/notifications/', 'GET', None),

    # Refunds
    ('/api/refunds/my-refunds/', 'GET', None),
    ('/api/refunds/stats/', 'GET', None),

    # Support
    ('/api/support/tickets/', 'GET', None),

    # Suppliers
    ('/api/suppliers/', 'GET', None),

    # Loyalty
    ('/api/loyalty/points/', 'GET', None),

    # Monitoring
    ('/api/monitoring/status/', 'GET', None),

    # Inventory
    ('/api/inventory/', 'GET', None),

    # Finance (payments)
    ('/api/payments/finance/summary/', 'GET', None),
    ('/api/payments/finance/transactions/', 'GET', None),
    ('/api/payments/finance/bank-accounts/', 'GET', None),

    # Pages (GET only, some require auth -> 302 or 200)
    ('/auth/login/', 'GET', 'page-login'),
    ('/auth/register/', 'GET', 'page-register'),
    ('/auth/register-mitra/', 'GET', 'page-register-mitra'),
    ('/auth/reset-password/', 'GET', 'page-reset-password'),
    ('/info/tentang-kami/', 'GET', 'page-tentang-kami'),
    ('/info/cara-belanja/', 'GET', 'page-cara-belanja'),
    ('/info/metode-pembayaran/', 'GET', 'page-metode-pembayaran'),
    ('/info/kontak-kami/', 'GET', 'page-kontak-kami'),
    ('/info/kebijakan/', 'GET', 'page-kebijakan'),
    ('/info/blog/', 'GET', 'page-blog'),
    ('/info/panduan-seller/', 'GET', 'page-panduan-seller'),
    ('/info/komunitas/', 'GET', 'page-komunitas'),
    ('/info/tips-sukses/', 'GET', 'page-tips-sukses'),
    ('/info/bantuan/', 'GET', 'page-bantuan'),
    ('/bantuan/', 'GET', 'page-bantuan-actual'),

    # Buyer pages (login_required -> 302)
    ('/buyer/home/', 'GET', 'page-buyer-home'),
    ('/buyer/products/', 'GET', 'page-buyer-products'),
    ('/buyer/dashboard/', 'GET', 'page-buyer-dashboard'),
    ('/buyer/orders/', 'GET', 'page-buyer-orders'),
    ('/buyer/cart/', 'GET', 'page-buyer-cart'),
    ('/buyer/checkout/', 'GET', 'page-buyer-checkout'),
    ('/buyer/profile/', 'GET', 'page-buyer-profile'),
    ('/buyer/wallet/', 'GET', 'page-buyer-wallet'),
    ('/buyer/reviews/', 'GET', 'page-buyer-reviews'),
    ('/buyer/favorites/', 'GET', 'page-buyer-favorites'),
    ('/buyer/promo/', 'GET', 'page-buyer-promo'),
    ('/buyer/settings/', 'GET', 'page-buyer-settings'),
    ('/buyer/loyalty/', 'GET', 'page-buyer-loyalty'),
    ('/buyer/chat/', 'GET', 'page-buyer-chat'),
    ('/buyer/refunds/', 'GET', 'page-buyer-refunds'),
    ('/buyer/order-detail/', 'GET', 'page-buyer-order-detail'),
    ('/buyer/order-success/', 'GET', 'page-buyer-order-success'),

    # Seller pages (login_required -> 302)
    ('/seller/dashboard/', 'GET', 'page-seller-dashboard'),
    ('/seller/pengiriman/', 'GET', 'page-seller-pengiriman'),
    ('/seller/products/', 'GET', 'page-seller-products'),
    ('/seller/orders/', 'GET', 'page-seller-orders'),
    ('/seller/laporan/', 'GET', 'page-seller-laporan'),
    ('/seller/keuangan/', 'GET', 'page-seller-keuangan'),
    ('/seller/pelanggan/', 'GET', 'page-seller-pelanggan'),
    ('/seller/pengaturan/', 'GET', 'page-seller-pengaturan'),
    ('/seller/promo-diskon/', 'GET', 'page-seller-promo-diskon'),
    ('/seller/ulasan/', 'GET', 'page-seller-ulasan'),
    ('/seller/supplier/', 'GET', 'page-seller-supplier'),
    ('/seller/refunds/', 'GET', 'page-seller-refunds'),
    ('/seller/partner-guide/', 'GET', 'page-seller-partner-guide'),
    ('/seller/stock-prediction/', 'GET', 'page-seller-stock-prediction'),

    # Admin pages
    ('/admin-panel/', 'GET', 'admin-dashboard'),
    ('/admin-panel/users/', 'GET', 'admin-users'),
    ('/admin-panel/marketplace/', 'GET', 'admin-marketplace'),
    ('/admin-panel/orders/', 'GET', 'admin-orders'),
    ('/admin-panel/payments/', 'GET', 'admin-payments'),
]

# All API POST endpoints to test
API_POST_ENDPOINTS = [
    ('/api/auth/register/', 'POST', '{"email":"audit2@test.com","password":"Test1234!","password2":"Test1234!","full_name":"Audit2","phone":"08123450002"}'),
    ('/api/auth/login/', 'POST', '{"email":"audit@test.com","password":"wrong"}'),
    ('/api/auth/logout/', 'POST', '{}'),
    ('/api/auth/token-refresh/', 'POST', '{}'),
    ('/api/auth/change-password/', 'POST', '{}'),
    ('/api/auth/otp/request/', 'POST', '{"email":"audit@test.com","purpose":"registration"}'),
    ('/api/auth/otp/verify/', 'POST', '{"email":"audit@test.com","otp_code":"123456","purpose":"registration"}'),
    ('/api/auth/forgot-password/', 'POST', '{"email":"audit@test.com"}'),
    ('/api/auth/reset-password/', 'POST', '{"email":"audit@test.com","otp_code":"123456","new_password":"Test1234!","new_password2":"Test1234!"}'),
    ('/api/auth/social/google/', 'POST', '{}'),
    ('/api/products/create/', 'POST', '{}'),
    ('/api/products/check-voucher/', 'POST', '{}'),
    ('/api/payments/wallet/topup/', 'POST', '{}'),
]

print("=" * 70)
print("  WARUNGIO PRODUCTION READINESS AUDIT")
print("=" * 70)

cookie_jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))

# Get initial CSRF cookie
try:
    opener.open(BASE + '/auth/login/', timeout=10)
except:
    pass

errors_500 = []
errors_404 = []
errors_other = []
success = []

def test_one(path, method, body_or_name):
    """Test a single endpoint."""
    url = BASE + path
    data = None
    headers = {}
    
    if method == 'POST' and body_or_name:
        data = body_or_name.encode() if isinstance(body_or_name, str) else json.dumps(body_or_name).encode()
        headers['Content-Type'] = 'application/json'
        # Try to send CSRF token if we have it
        for c in cookie_jar:
            if c.name == 'csrftoken':
                headers['X-CSRFToken'] = c.value
                break
    
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    
    try:
        resp = opener.open(req, timeout=15)
        code = resp.status
        if code >= 500:
            errors_500.append((path, method, f"HTTP {code}", resp.read().decode()[:300]))
        elif code == 404:
            errors_404.append((path, method, f"HTTP {code}"))
        elif code >= 400:
            errors_other.append((path, method, f"HTTP {code}"))
        else:
            success.append((path, method, code))
        return code, None
    except urllib.error.HTTPError as e:
        code = e.code
        body = e.read().decode('utf-8', errors='replace')[:500]
        if code >= 500:
            errors_500.append((path, method, body, ''))
        elif code == 404:
            errors_404.append((path, method, body[:100]))
        elif code >= 400:
            errors_other.append((path, method, f"HTTP {code}: {body[:80]}"))
        return code, body
    except Exception as e:
        errors_500.append((path, method, str(e)[:200], traceback.format_exc()))
        return None, str(e)

print("\n--- TESTING ALL ENDPOINTS ---\n")

for path, method, body_or_name in ENDPOINTS:
    code, _ = test_one(path, method, body_or_name)
    label = f"{'[%s]' % method:6s} {path:55s}"
    if code is None:
        print(f"  ERR   {label}")
    elif code >= 500:
        print(f"  {code}  {label}  *** 500 ERROR ***")
    elif code == 404:
        print(f"  {code}  {label}")
    elif code == 302:
        print(f"  {code}  {label}  (redirect - expected: login_required)")
    elif code >= 400:
        print(f"  {code}  {label}  (expected if auth required)")
    else:
        print(f"  {code}  {label}")

print("\n" + "=" * 70)
print("  AUDIT SUMMARY")
print("=" * 70)
print(f"  Total endpoints tested: {len(ENDPOINTS)}")
print(f"  HTTP 200/201/204:       {len([s for s in success if s[2] in (200,201,204)])}")
print(f"  HTTP 302 (redirect):    {len([s for s in success if s[2] == 302])}")
print(f"  HTTP 500 errors:        {len(errors_500)}")
print(f"  HTTP 404 errors:        {len(errors_404)}")
print(f"  HTTP 4xx (other):       {len(errors_other)}")

if errors_500:
    print("\n" + "!" * 70)
    print("  HTTP 500 ERRORS — REQUIRES IMMEDIATE FIX")
    print("!" * 70)
    for path, method, body, tb in errors_500:
        print(f"\n  {method} {path}")
        # Try to extract meaningful error
        err_msg = body[:300] if body else 'No response body'
        print(f"    Response: {err_msg}")

if errors_404:
    print("\n--- HTTP 404 ERRORS ---")
    for path, method, body in errors_404:
        print(f"  {method} {path:55s} {body[:80]}")

if errors_other:
    print("\n--- OTHER 4xx ERRORS ---")
    for path, method, body in errors_other:
        print(f"  {method} {path:55s} {body[:80]}")

print("\nDone.")
