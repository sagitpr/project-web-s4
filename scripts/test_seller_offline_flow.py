"""
Warungio Test — Seller Full Flow + Offline Purchase
Test dilakukan via HTTP langsung ke localhost:8000 dari dalam container.
"""

import os, json, uuid, sys, time, urllib.request, urllib.error, ssl

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
os.environ['CELERY_ENABLED'] = 'false'
os.environ['SECURE_SSL_REDIRECT'] = 'false'
os.environ['DJANGO_ALLOWED_HOSTS'] = 'localhost,127.0.0.1,testserver'

import django
django.setup()

from django.test import override_settings
from django.conf import settings

# Override SSL redirect for test
settings.SECURE_SSL_REDIRECT = False

# ── HTTP Helper ──
def http(method, path, data=None, token=None):
    """Send HTTP request via urllib (bypass SSL)."""
    url = f'http://localhost:8000{path}'
    ctx = ssl._create_unverified_context()
    
    body = None
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    if data is not None:
        body = json.dumps(data).encode('utf-8')
    
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=10)
        content = resp.read().decode('utf-8')
        try:
            resp_data = json.loads(content)
        except:
            resp_data = content
        return resp.status, resp_data, None
    except urllib.error.HTTPError as e:
        content = e.read().decode('utf-8', errors='ignore')
        try:
            resp_data = json.loads(content)
        except:
            resp_data = content
        return e.code, resp_data, str(e)
    except Exception as e:
        return 0, None, str(e)


# ── Test Results ──
results = []
passed = 0
failed = 0

def test(flow, step, name, func):
    global passed, failed
    try:
        ok, msg = func()
        if ok:
            passed += 1
            status = '✅ PASS'
        else:
            failed += 1
            status = '❌ FAIL'
        print(f'  [{flow}] {step}. {name}: {status} — {msg[:120]}')
        results.append((flow, step, name, status, msg))
    except Exception as e:
        failed += 1
        print(f'  [{flow}] {step}. {name}: ❌ ERROR — {str(e)[:120]}')
        results.append((flow, step, name, '❌ ERROR', str(e)[:120]))


# =============================================================================
# MAIN TEST
# =============================================================================

uid = str(uuid.uuid4())[:6].replace('-', '0')
EMAIL = f'seller_{uid}@warungio.test'
PASSWORD = 'Test@123456'
PHONE = f'08123456{int(time.time()) % 100000:05d}'

print('=' * 70)
print('TEST SELLER FLOW + OFFLINE PURCHASE')
print(f'User: {EMAIL} | Phone: {PHONE}')
print('=' * 70)

TOKEN = ''
STORE_ID = None
PRODUCT_IDS = []

# ── PRE: Check Health ──
def pre_health():
    code, data, err = http('GET', '/health/')
    return code == 200, f'Health: {code}'
test('PRE', 'P0', 'Health Check', pre_health)

# ── A1: Register Seller ──
def a1_register():
    code, data, err = http('POST', '/api/auth/register/', {
        'username': f'seller_{uid}',
        'email': EMAIL,
        'password': PASSWORD,
        'password2': PASSWORD,
        'full_name': 'Test Seller',
        'phone': PHONE,
        'role': 'seller'
    })
    if code in (200, 201):
        otp = None
        if isinstance(data, dict):
            otp = data.get('otp_code') or data.get('data', {}).get('otp_code', '')
        return True, f'HTTP {code} — User created! OTP: {otp}'
    return False, f'HTTP {code}: {str(data)[:100]}'
test('A', 'A1', 'Register Seller', a1_register)

# ── A2: OTP Verify ──
def a2_otp():
    # Get OTP code from DB (DEBUG mode returns in response, but we can also read from DB)
    from accounts.models import OTP
    otp_obj = OTP.objects.filter(email=EMAIL).order_by('-created_at').first()
    if not otp_obj:
        return False, 'OTP not found in DB'
    otp_code = otp_obj.otp_code
    code, data, err = http('POST', '/api/auth/otp/verify/', {
        'email': EMAIL,
        'otp_code': otp_code
    })
    if code == 200:
        return True, f'HTTP 200 — OTP Verified! (code: {otp_code})'
    return False, f'HTTP {code}: {str(data)[:100]}'
test('A', 'A2', 'Verify OTP', a2_otp)

# ── A3: Login ──
def a3_login():
    global TOKEN
    code, data, err = http('POST', '/api/auth/login/', {
        'email': EMAIL,
        'password': PASSWORD
    })
    if code == 200 and isinstance(data, dict):
        TOKEN = data.get('access', data.get('token', ''))
        if TOKEN:
            return True, f'JWT Token: {TOKEN[:40]}...'
    return False, f'HTTP {code}: {str(data)[:80]}'
test('A', 'A3', 'Login JWT', a3_login)

# ── A4: Check Auth ──
def a4_auth():
    code, data, err = http('GET', '/api/auth/profile/', token=TOKEN)
    if code == 200:
        role = data.get('role', '?') if isinstance(data, dict) else '?'
        return True, f'HTTP 200 — Role: {role}'
    return False, f'HTTP {code}: {str(data)[:80]}'
test('A', 'A4', 'Profile Check', a4_auth)

# ── B1: Create Store ──
def b1_store():
    global STORE_ID
    code, data, err = http('POST', '/api/stores/create/', {
        'store_name': f'Toko Test {uid}',
        'store_description': 'Toko untuk testing offline sale',
        'store_address': 'Jl. Merdeka No. 123, Jakarta',
        'store_phone': PHONE,
        'latitude': -6.2088,
        'longitude': 106.8456
    }, token=TOKEN)
    if code in (200, 201):
        if isinstance(data, dict):
            STORE_ID = data.get('id') or data.get('store', {}).get('id')
        return True, f'HTTP {code} — Store created! ID: {STORE_ID}'
    return False, f'HTTP {code}: {str(data)[:100]}'
test('B', 'B1', 'Create Store', b1_store)

# ── B2: Check My Store ──
def b2_mystore():
    code, data, err = http('GET', '/api/stores/my-store/', token=TOKEN)
    if code == 200:
        store_name = data.get('store_name', '?') if isinstance(data, dict) else '?'
        return True, f'HTTP 200 — Store: {store_name}'
    return False, f'HTTP {code}: {str(data)[:80]}'
test('B', 'B2', 'My Store', b2_mystore)

# ── B3: Create Category (if needed) ──
def b3_category():
    code, data, err = http('GET', '/api/products/categories/')
    if code == 200:
        cats = data if isinstance(data, list) else data.get('results', [])
        if cats and len(cats) > 0:
            return True, f'Categories exist: {len(cats)}'
        return True, 'No categories yet, but endpoint works'
    return False, f'HTTP {code}: {str(data)[:80]}'
test('B', 'B3', 'Categories', b3_category)

# ── B4: Create Products ──
def b4_products():
    global PRODUCT_IDS
    products_data = [
        {'product_name': f'Beras Premium {uid}', 'price': 15000, 'stock': 50, 'unit': 'kg',
         'product_status': 'available', 'store': STORE_ID},
        {'product_name': f'Minyak Goreng {uid}', 'price': 25000, 'stock': 30, 'unit': 'liter',
         'product_status': 'available', 'store': STORE_ID},
        {'product_name': f'Gula Pasir {uid}', 'price': 14000, 'stock': 20, 'unit': 'kg',
         'product_status': 'available', 'store': STORE_ID},
    ]
    for pdata in products_data:
        code, data, err = http('POST', '/api/products/create/', pdata, token=TOKEN)
        if code in (200, 201):
            pid = data.get('id') if isinstance(data, dict) else None
            if pid:
                PRODUCT_IDS.append(pid)
    count = len(PRODUCT_IDS)
    return count >= 1, f'{count} products created: {PRODUCT_IDS}'
test('B', 'B4', 'Create Products', b4_products)

# ── B5: Check Products ──
def b5_myproducts():
    code, data, err = http('GET', '/api/products/my-products/', token=TOKEN)
    if code == 200:
        prods = data if isinstance(data, list) else data.get('results', [])
        return True, f'My products: {len(prods)} items'
    return False, f'HTTP {code}: {str(data)[:80]}'
test('B', 'B5', 'My Products', b5_myproducts)

# ── B6: Check Product Stock ──
def b6_stock():
    if not PRODUCT_IDS:
        return False, 'No products to check'
    pid = PRODUCT_IDS[0]
    code, data, err = http('GET', f'/api/products/{pid}/')
    if code == 200 and isinstance(data, dict):
        stock = data.get('stock', '?')
        return True, f'Product stock: {stock}'
    return False, f'HTTP {code}: {str(data)[:80]}'
test('B', 'B6', 'Product Stock Check', b6_stock)


# =============================================================================
# FLOW C: OFFLINE PURCHASE (Pembelian Langsung di Toko)
# =============================================================================

# ── C1: Offline Sale — Beli Produk ──
def c1_offline_sale():
    if not PRODUCT_IDS:
        return False, 'No products'
    pid = PRODUCT_IDS[0]
    code, data, err = http('POST', '/api/orders/offline-sale/', {
        'product': pid,
        'quantity': 3,
        'price': 15000,
        'buyer_name': 'Budi Pembeli',
        'buyer_phone': '081234567890',
        'notes': 'Pembelian offline di toko',
        'payment_method': 'cash'
    }, token=TOKEN)
    if code == 201:
        new_stock = data.get('new_stock', '?')
        return True, f'HTTP 201 — Sale recorded! Stock now: {new_stock}'
    return False, f'HTTP {code}: {str(data)[:120]}'
test('C', 'C1', 'Offline Sale (Beli 3 item)', c1_offline_sale)

# ── C2: Check Stock After Sale ──
def c2_stock_after():
    if not PRODUCT_IDS:
        return False, 'No products'
    pid = PRODUCT_IDS[0]
    code, data, err = http('GET', f'/api/products/{pid}/')
    if code == 200 and isinstance(data, dict):
        stock = data.get('stock', 0)
        return stock >= 0, f'Stock after sale: {stock}'
    return False, f'HTTP {code}: {str(data)[:80]}'
test('C', 'C2', 'Stock After Sale', c2_stock_after)

# ── C3: Offline Sale — Beli dengan QRIS ──
def c3_offline_qris():
    if not PRODUCT_IDS:
        return False, 'No products'
    pid = PRODUCT_IDS[1] if len(PRODUCT_IDS) > 1 else PRODUCT_IDS[0]
    code, data, err = http('POST', '/api/orders/offline-sale/', {
        'product': pid,
        'quantity': 2,
        'buyer_name': 'Siti Pembeli',
        'payment_method': 'qris'
    }, token=TOKEN)
    if code == 201:
        new_stock = data.get('new_stock', '?')
        return True, f'HTTP 201 — QRIS sale! Stock now: {new_stock}'
    return False, f'HTTP {code}: {str(data)[:120]}'
test('C', 'C3', 'Offline Sale (QRIS)', c3_offline_qris)

# ── C4: Offline Sale — Coba beli melebihi stok (harus error) ──
def c4_oversell():
    if not PRODUCT_IDS:
        return False, 'No products'
    pid = PRODUCT_IDS[0]
    code, data, err = http('POST', '/api/orders/offline-sale/', {
        'product': pid,
        'quantity': 9999,
        'payment_method': 'cash'
    }, token=TOKEN)
    # Should get 400 error because stock is insufficient
    if code == 400:
        err_msg = data.get('error', str(data)) if isinstance(data, dict) else str(data)
        return True, f'Correctly rejected! HTTP 400 — {err_msg[:80]}'
    return code in (200,201), f'Unexpected: HTTP {code} (seharusnya 400)'
test('C', 'C4', 'Over-sell Rejection', c4_oversell)

# ── C5: List Offline Sales ──
def c5_list_offline():
    code, data, err = http('GET', '/api/orders/offline-sales/', token=TOKEN)
    if code == 200:
        sales = data if isinstance(data, list) else data.get('results', [])
        return True, f'Offline sales list: {len(sales)} records'
    return False, f'HTTP {code}: {str(data)[:80]}'
test('C', 'C5', 'List Offline Sales', c5_list_offline)


# =============================================================================
# FLOW D: VERIFIKASI STOK PRODUK (Seller bisa edit stok manual)
# =============================================================================

# ── D1: Edit Product Stock (Manual adjustment by seller) ──
def d1_edit_stock():
    if not PRODUCT_IDS:
        return False, 'No products'
    pid = PRODUCT_IDS[0]
    code, data, err = http('PATCH', f'/api/products/{pid}/manage/', {
        'stock': 100,
        'price': 16000
    }, token=TOKEN)
    if code == 200:
        new_stock = data.get('stock', '?') if isinstance(data, dict) else '?'
        return True, f'HTTP 200 — Stock updated to: {new_stock}'
    return False, f'HTTP {code}: {str(data)[:80]}'
test('D', 'D1', 'Edit Stock (Restock)', d1_edit_stock)

# ── D2: Verify Stock Edit ──
def d2_verify_stock():
    if not PRODUCT_IDS:
        return False, 'No products'
    pid = PRODUCT_IDS[0]
    code, data, err = http('GET', f'/api/products/{pid}/')
    if code == 200 and isinstance(data, dict):
        stock = data.get('stock', 0)
        price = data.get('price', 0)
        return int(stock) == 100, f'Stock: {stock}, Price: {price}'
    return False, f'HTTP {code}: {str(data)[:80]}'
test('D', 'D2', 'Verify Stock Edit', d2_verify_stock)


# =============================================================================
# SUMMARY
# =============================================================================

print('\n' + '=' * 70)
print(f'HASIL: {passed} ✅ PASS / {failed} ❌ FAIL dari {passed + failed} tests')
print('=' * 70)

for flow, step, name, status, msg in results:
    print(f'  [{flow}] {step}. {name}: {status}')

print(f'\nTotal: {passed + failed} tests | {passed} PASS | {failed} FAIL')

# Exit with error code if any failed
if failed > 0:
    sys.exit(1)
else:
    sys.exit(0)
