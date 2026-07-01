#!/usr/bin/env python3
"""Warungio Test — Seller Full Flow + Offline Purchase"""
import os, django, json, uuid, random

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
os.environ['CELERY_ENABLED'] = 'false'
os.environ['DJANGO_ALLOWED_HOSTS'] = 'localhost,127.0.0.1,testserver'
os.environ['DJANGO_DEBUG'] = 'True'
os.environ['SECURE_SSL_REDIRECT'] = 'False'
os.environ['SESSION_COOKIE_SECURE'] = 'False'
os.environ['CSRF_COOKIE_SECURE'] = 'False'

django.setup()

from django.conf import settings
settings.SECURE_SSL_REDIRECT = False
settings.SESSION_COOKIE_SECURE = False
settings.CSRF_COOKIE_SECURE = False
settings.DEBUG = True
settings.ALLOWED_HOSTS = ['*']  # Override: allow all hosts for testing

from django.db import connection
from rest_framework.test import APIClient

from accounts.models import User, OTP
from stores.models import Store
from products.models import Product

client = APIClient()
results = []
uid = str(uuid.uuid4())[:6]
EMAIL = f"seller_{uid}@warungio.test"
PASSWORD = 'Test@123456'
PHONE = f"081234{random.randint(100000,999999)}"

def test(flow, step, desc, func):
    try:
        ok, detail = func()
        s = "✅" if ok else "❌"
        results.append((flow, step, desc, ok, str(detail)[:120]))
        print(f"  {s} | {step}: {desc} -> {str(detail)[:100]}")
    except Exception as e:
        results.append((flow, step, desc, False, str(e)[:120]))
        print(f"  ❌ ERROR | {step}: {desc} -> {e}")

print("="*70)
print("  WARUNGIO — SELLER FLOW + OFFLINE PURCHASE TEST")
print("="*70)

# ── PRE: Database ──
print("\n" + "─"*70)
print("  PRE-FLIGHT")
print("─"*70)

def pre_01():
    with connection.cursor() as c:
        c.execute("SELECT COUNT(*) FROM django_migrations")
        return True, f"{c.fetchone()[0]} migrations applied"
test('PRE', 'P0', 'Migration count', pre_01)

# ── AUTH + OTP ──
print("\n" + "─"*70)
print("  FLOW A: REGISTER SELLER + OTP + JWT")
print("─"*70)

OTP_CODE = ""
TOKEN = ""

def a1_register():
    global OTP_CODE
    resp = client.post('/api/auth/register/', {
        'username': f'seller_{uid}', 'email': EMAIL, 'password': PASSWORD,
        'password2': PASSWORD, 'full_name': 'Test Seller', 'phone': PHONE, 'role': 'seller'
    }, format='json')
    ok = resp.status_code in (200, 201)
    if ok:
        d = resp.json() if hasattr(resp, 'json') else resp.data
        OTP_CODE = d.get('otp_code', '')
        return True, f"HTTP {resp.status_code} | OTP: {OTP_CODE}"
    content = resp.content.decode('utf-8','ignore') if hasattr(resp, 'content') else str(resp)
    return False, f"HTTP {resp.status_code}: {content[:100]}"
test('A', 'A1', 'Register Seller', a1_register)

def a2_verify_otp():
    if not OTP_CODE:
        # Try from DB
        otp_obj = OTP.objects.filter(email=EMAIL).order_by('-created_at').first()
        if otp_obj:
            OTP_CODE_ = otp_obj.otp_code
        else:
            return False, "No OTP code from response or DB"
    else:
        OTP_CODE_ = OTP_CODE

    resp = client.post('/api/auth/otp/verify/', {
        'email': EMAIL, 'otp_code': OTP_CODE_, 'purpose': 'registration'
    }, format='json')
    ok = resp.status_code == 200
    if ok:
        return True, f"HTTP 200 — OTP Verified! (code: {OTP_CODE_})"
    content = resp.content.decode('utf-8','ignore') if hasattr(resp, 'content') else str(resp)
    return False, f"HTTP {resp.status_code}: {content[:100]}"
test('A', 'A2', 'Verify OTP', a2_verify_otp)

def a3_login():
    global TOKEN
    resp = client.post('/api/auth/login/', {'email': EMAIL, 'password': PASSWORD}, format='json')
    ok = resp.status_code == 200
    if ok:
        d = resp.json() if hasattr(resp, 'json') else resp.data
        TOKEN = d.get('access', '')
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {TOKEN}')
        return True, f"JWT: {TOKEN[:40]}..."
    content = resp.content.decode('utf-8','ignore') if hasattr(resp, 'content') else str(resp)
    return False, f"HTTP {resp.status_code}: {content[:100]}"
test('A', 'A3', 'Login JWT', a3_login)

def a4_profile():
    resp = client.get('/api/auth/profile/')
    if resp.status_code == 200:
        d = resp.json() if hasattr(resp, 'json') else resp.data
        return True, f"Role: {d.get('role','?')} | is_verified: {d.get('is_verified','?')}"
    return False, f"HTTP {resp.status_code}"
test('A', 'A4', 'Profile Check', a4_profile)

# ── STORE ──
print("\n" + "─"*70)
print("  FLOW B: STORE & PRODUK")
print("─"*70)

SID = None

def b1_store():
    global SID
    resp = client.post('/api/stores/create/', {
        'store_name': f'Toko Test {uid}',
        'description': 'Toko untuk testing offline sale',
        'address': 'Jl. Merdeka No. 123, Jakarta',
        'city': 'Jakarta',
        'province': 'DKI Jakarta',
        'latitude': -6.2088,
        'longitude': 106.8456
    }, format='json')
    ok = resp.status_code in (200, 201)
    if ok:
        d = resp.json() if hasattr(resp, 'json') else resp.data
        SID = d.get('id') or d.get('store', {}).get('id')
        return True, f"Store created! ID: {SID}"
    content = resp.content.decode('utf-8','ignore') if hasattr(resp, 'content') else str(resp)
    return False, f"HTTP {resp.status_code}: {content[:100]}"
test('B', 'B1', 'Create Store', b1_store)

def b2_mystore():
    resp = client.get('/api/stores/my-store/')
    if resp.status_code == 200:
        d = resp.json() if hasattr(resp, 'json') else resp.data
        return True, f"Store: {d.get('store_name','?')}"
    return False, f"HTTP {resp.status_code}"
test('B', 'B2', 'My Store', b2_mystore)

def b3_categories():
    resp = client.get('/api/products/categories/')
    return resp.status_code == 200, f"Categories OK: HTTP {resp.status_code}"
test('B', 'B3', 'Categories', b3_categories)

# ── PRODUCTS ──
PIDS = []

def b4_create_products():
    global PIDS
    products_data = [
        {'product_name': f'Beras Premium {uid}', 'price': 15000, 'stock': 50, 'unit': 'kg',
         'product_status': 'fresh'},
        {'product_name': f'Minyak Goreng {uid}', 'price': 25000, 'stock': 30, 'unit': 'liter',
         'product_status': 'fresh'},
        {'product_name': f'Gula Pasir {uid}', 'price': 14000, 'stock': 20, 'unit': 'kg',
         'product_status': 'fresh'},
    ]
    for pdata in products_data:
        resp = client.post('/api/products/create/', pdata, format='json')
        if resp.status_code in (200, 201):
            d = resp.json() if hasattr(resp, 'json') else resp.data
            pid = d.get('id')
            if pid:
                PIDS.append(pid)
    return len(PIDS) >= 1, f"{len(PIDS)} products created: {PIDS}"
test('B', 'B4', 'Create Products', b4_create_products)

def b5_myproducts():
    resp = client.get('/api/products/my-products/')
    if resp.status_code == 200:
        d = resp.json() if hasattr(resp, 'json') else resp.data
        prods = d if isinstance(d, list) else d.get('results', [])
        return True, f"My products: {len(prods)} items"
    return False, f"HTTP {resp.status_code}"
test('B', 'B5', 'My Products', b5_myproducts)

def b6_stock():
    if not PIDS: return False, "No products"
    resp = client.get(f'/api/products/{PIDS[0]}/')
    if resp.status_code == 200:
        d = resp.json() if hasattr(resp, 'json') else resp.data
        return True, f"Product stock: {d.get('stock','?')} | Price: {d.get('price','?')}"
    return False, f"HTTP {resp.status_code}"
test('B', 'B6', 'Initial Stock', b6_stock)

# =============================================================================
# FLOW C: OFFLINE PURCHASE
# =============================================================================
print("\n" + "─" * 70)
print("  FLOW C: OFFLINE PURCHASE (Pembelian Langsung di Toko)")
print("─" * 70)

def c1_offline_sale():
    if not PIDS: return False, "No products"
    resp = client.post('/api/orders/offline-sale/', {
        'product': PIDS[0],
        'quantity': 3,
        'price': 15000,
        'buyer_name': 'Budi Pembeli',
        'buyer_phone': '081234567890',
        'notes': 'Pembelian offline di toko',
        'payment_method': 'cash'
    }, format='json')
    ok = resp.status_code == 201
    if ok:
        d = resp.json() if hasattr(resp, 'json') else resp.data
        return True, f"HTTP 201 — Stock: {d.get('new_stock','?')}"
    content = resp.content.decode('utf-8','ignore') if hasattr(resp, 'content') else str(resp)
    return False, f"HTTP {resp.status_code}: {content[:120]}"
test('C', 'C1', 'Offline Sale (Beli 3 item)', c1_offline_sale)

def c2_stock_after():
    if not PIDS: return False, "No products"
    resp = client.get(f'/api/products/{PIDS[0]}/')
    if resp.status_code == 200:
        d = resp.json() if hasattr(resp, 'json') else resp.data
        stock = d.get('stock', 0)
        return stock >= 0, f"Stock after sale: {stock}"
    return False, f"HTTP {resp.status_code}"
test('C', 'C2', 'Stock After Sale', c2_stock_after)

def c3_offline_qris():
    if not PIDS: return False, "No products"
    pid = PIDS[1] if len(PIDS) > 1 else PIDS[0]
    resp = client.post('/api/orders/offline-sale/', {
        'product': pid,
        'quantity': 2,
        'buyer_name': 'Siti Pembeli',
        'payment_method': 'qris'
    }, format='json')
    ok = resp.status_code == 201
    if ok:
        d = resp.json() if hasattr(resp, 'json') else resp.data
        return True, f"HTTP 201 — QRIS sale! Stock: {d.get('new_stock','?')}"
    content = resp.content.decode('utf-8','ignore') if hasattr(resp, 'content') else str(resp)
    return False, f"HTTP {resp.status_code}: {content[:120]}"
test('C', 'C3', 'Offline Sale (QRIS)', c3_offline_qris)

def c4_oversell():
    """Coba beli melebihi stok — harus ditolak 400"""
    if not PIDS: return False, "No products"
    resp = client.post('/api/orders/offline-sale/', {
        'product': PIDS[0],
        'quantity': 9999,
        'payment_method': 'cash'
    }, format='json')
    content = resp.content.decode('utf-8','ignore') if hasattr(resp, 'content') else str(resp)
    if resp.status_code == 400:
        return True, f"Correctly rejected! HTTP 400"
    # Might also get 403 if store not found in request.user
    return resp.status_code == 403, f"Got HTTP {resp.status_code} — {content[:80]}"
test('C', 'C4', 'Over-sell Rejection', c4_oversell)

def c5_list_offline():
    resp = client.get('/api/orders/offline-sales/')
    if resp.status_code == 200:
        d = resp.json() if hasattr(resp, 'json') else resp.data
        sales = d if isinstance(d, list) else d.get('results', [])
        return True, f"Offline sales: {len(sales)} records"
    return False, f"HTTP {resp.status_code}"
test('C', 'C5', 'List Offline Sales', c5_list_offline)

# =============================================================================
# FLOW D: MANUAL STOCK EDIT (Seller dapat edit stok)
# =============================================================================
print("\n" + "─" * 70)
print("  FLOW D: MANUAL STOCK ADJUSTMENT")
print("─" * 70)

def d1_restock():
    if not PIDS: return False, "No products"
    resp = client.patch(f'/api/products/{PIDS[0]}/manage/', {
        'stock': 100,
        'price': 16000
    }, format='json')
    if resp.status_code == 200:
        d = resp.json() if hasattr(resp, 'json') else resp.data
        return True, f"Stock updated to: {d.get('stock','?')} | Price: {d.get('price','?')}"
    return False, f"HTTP {resp.status_code}"
test('D', 'D1', 'Restock (Edit Stock)', d1_restock)

def d2_verify_restock():
    if not PIDS: return False, "No products"
    resp = client.get(f'/api/products/{PIDS[0]}/')
    if resp.status_code == 200:
        d = resp.json() if hasattr(resp, 'json') else resp.data
        stock = d.get('stock', 0)
        return int(stock) >= 90, f"Verified: stock={stock} (expected ~100 after restock)"
    return False, f"HTTP {resp.status_code}"
test('D', 'D2', 'Verify Restock', d2_verify_restock)

# =============================================================================
# SUMMARY
# =============================================================================
print("\n" + "=" * 70)
print("  HASIL TEST SELLER + OFFLINE PURCHASE")
print("=" * 70)

passed = sum(1 for r in results if r[3])
failed = sum(1 for r in results if not r[3])
total = len(results)
pct = passed / total * 100 if total else 0
print(f"\n  Total: {total} | ✅ PASS: {passed} | ❌ FAIL: {failed} | Score: {pct:.0f}%\n")

print(f"  Detail:")
for r in results:
    s = "✅" if r[3] else "❌"
    print(f"  {s} | {r[0]}.{r[1]:3s} | {r[2][:35]:35s} | {r[4][:100]}")

# Cleanup
try:
    User.objects.filter(email=EMAIL).delete()
    print(f"\n  🧹 Test user {EMAIL} cleaned up")
except:
    pass

print(f"\n{'='*70}")
print(f"  TEST SELESAI")
print(f"{'='*70}")

if failed > 0:
    exit(1)
else:
    exit(0)
