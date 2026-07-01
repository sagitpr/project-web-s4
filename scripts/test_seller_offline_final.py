#!/usr/bin/env python3
"""Warungio Test — Seller Full Flow + Offline Purchase (FINAL).
Semua setting di-override sebelum Django startup.
"""
import os, django, uuid, random, sys

# ── Override settings BEFORE django.setup() ──
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
os.environ['CELERY_ENABLED'] = 'false'
os.environ['SECURE_SSL_REDIRECT'] = 'False'
os.environ['SESSION_COOKIE_SECURE'] = 'False'
os.environ['CSRF_COOKIE_SECURE'] = 'False'
os.environ['SECURE_HSTS_SECONDS'] = '0'
os.environ['DJANGO_DEBUG'] = 'True'

django.setup()

# ── Force override settings ──
from django.conf import settings
settings.DEBUG = True
settings.SECURE_SSL_REDIRECT = False
settings.SESSION_COOKIE_SECURE = False
settings.CSRF_COOKIE_SECURE = False
settings.SECURE_HSTS_SECONDS = 0
settings.ALLOWED_HOSTS = ['*']
# Biarkan RECAPTCHA_SECRET_KEY kosong agar bypass di DEBUG mode

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
print("  WARUNGIO — SELLER + OFFLINE PURCHASE FINAL TEST")
print("="*70)

# ── PRE ──
print("\n" + "─"*70)
print("  PRE-FLIGHT")
print("─"*70)

def pre_01():
    with connection.cursor() as c:
        c.execute("SELECT COUNT(*) FROM django_migrations")
        return True, f"{c.fetchone()[0]} migrations applied"
test('PRE', 'P0', 'Migration count', pre_01)

# ── AUTH ──
print("\n" + "─"*70)
print("  FLOW A: REGISTER SELLER + OTP + JWT")
print("─"*70)

OTP_CODE = ""
TOKEN = ""

def a1_register():
    global OTP_CODE
    resp = client.post('/api/auth/register/', {
        'username': f'seller_{uid}', 'email': EMAIL, 'password': PASSWORD,
        'password2': PASSWORD, 'full_name': 'Test Seller', 'phone': PHONE, 'role': 'seller',
        'captcha_token': 'bypass'
    }, format='json')
    ok = resp.status_code in (200, 201)
    if ok:
        d = resp.json()
        OTP_CODE = d.get('otp_code', '')
        return True, f"HTTP {resp.status_code} | OTP: {OTP_CODE}"
    content = resp.content.decode('utf-8','ignore')
    return False, f"HTTP {resp.status_code}: {content[:200]}"
test('A', 'A1', 'Register Seller', a1_register)

def a2_verify_otp():
    code = OTP_CODE
    if not code:
        otp_obj = OTP.objects.filter(email=EMAIL).order_by('-created_at').first()
        code = otp_obj.otp_code if otp_obj else ''
    if not code:
        return False, "No OTP code available"
    resp = client.post('/api/auth/otp/verify/', {
        'email': EMAIL, 'otp_code': code, 'purpose': 'registration'
    }, format='json')
    return resp.status_code == 200, f"HTTP {resp.status_code} — OTP: {code}"
test('A', 'A2', 'Verify OTP', a2_verify_otp)

def a3_login():
    global TOKEN
    resp = client.post('/api/auth/login/', {'email': EMAIL, 'password': PASSWORD}, format='json')
    if resp.status_code == 200:
        d = resp.json()
        TOKEN = d.get('access', '')
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {TOKEN}')
        return True, f"JWT: {TOKEN[:40]}..."
    content = resp.content.decode('utf-8','ignore')
    return False, f"HTTP {resp.status_code}: {content[:100]}"
test('A', 'A3', 'Login JWT', a3_login)

def a4_profile():
    resp = client.get('/api/auth/profile/')
    if resp.status_code == 200:
        d = resp.json()
        return True, f"Role: {d.get('role','?')} | Verified: {d.get('is_verified','?')}"
    return False, f"HTTP {resp.status_code}"
test('A', 'A4', 'Profile Check', a4_profile)

# ── STORE ──
print("\n" + "─"*70)
print("  FLOW B: STORE & PRODUK")
print("─"*70)

SID = None
PIDS = []

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
        # Get ID from my-store endpoint (serializer doesn't include id)
        resp2 = client.get('/api/stores/my-store/')
        if resp2.status_code == 200:
            SID = resp2.json().get('id')
        return True, f"Store created! ID: {SID}"
    content = resp.content.decode('utf-8','ignore')
    return False, f"HTTP {resp.status_code}: {content[:200]}"
test('B', 'B1', 'Create Store', b1_store)

def b2_mystore():
    resp = client.get('/api/stores/my-store/')
    if resp.status_code == 200:
        d = resp.json()
        return True, f"Store: {d.get('store_name','?')}"
    return False, f"HTTP {resp.status_code}"
test('B', 'B2', 'My Store', b2_mystore)

def b3_categories():
    resp = client.get('/api/products/categories/')
    return resp.status_code == 200, f"HTTP {resp.status_code}"
test('B', 'B3', 'Categories', b3_categories)

def b4_create_products():
    global PIDS
    prods = [
        {'product_name': f'Beras Premium {uid}', 'price': 15000, 'stock': 50, 'unit': 'kg', 'product_status': 'fresh'},
        {'product_name': f'Minyak Goreng {uid}', 'price': 25000, 'stock': 30, 'unit': 'liter', 'product_status': 'fresh'},
        {'product_name': f'Gula Pasir {uid}', 'price': 14000, 'stock': 20, 'unit': 'kg', 'product_status': 'fresh'},
    ]
    for p in prods:
        resp = client.post('/api/products/create/', p, format='json')
        ok = resp.status_code in (200, 201)
        if not ok:
            err = resp.content.decode('utf-8','ignore')[:100]
            return False, f"Product create failed! HTTP {resp.status_code}: {err}"
    # Get IDs from my-products endpoint (serializer doesn't include id)
    resp = client.get('/api/products/my-products/')
    if resp.status_code == 200:
        d = resp.json()
        items = d if isinstance(d, list) else d.get('results', [])
        PIDS = [item['id'] for item in items if 'id' in item]
    return len(PIDS) >= 1, f"{len(PIDS)} products: {PIDS}"
test('B', 'B4', 'Create Products', b4_create_products)

def b5_myproducts():
    resp = client.get('/api/products/my-products/')
    if resp.status_code == 200:
        d = resp.json()
        prods = d if isinstance(d, list) else d.get('results', [])
        return True, f"{len(prods)} products"
    return False, f"HTTP {resp.status_code}"
test('B', 'B5', 'My Products', b5_myproducts)

def b6_stock_check():
    if not PIDS: return False, "No products"
    resp = client.get(f'/api/products/{PIDS[0]}/')
    if resp.status_code == 200:
        d = resp.json()
        return True, f"Stock: {d.get('stock','?')}, Price: {d.get('price','?')}"
    return False, f"HTTP {resp.status_code}"
test('B', 'B6', 'Product Stock', b6_stock_check)

# ── OFFLINE SALE ──
print("\n" + "─" * 70)
print("  FLOW C: OFFLINE PURCHASE")
print("─" * 70)

def c1_offline_sale():
    if not PIDS: return False, "No products"
    resp = client.post('/api/orders/offline-sale/', {
        'product': PIDS[0], 'quantity': 3, 'price': 15000,
        'buyer_name': 'Budi', 'buyer_phone': '081234567890',
        'notes': 'Offline purchase', 'payment_method': 'cash'
    }, format='json')
    ok = resp.status_code == 201
    if ok:
        return True, f"HTTP 201 — Stock: {resp.json().get('new_stock','?')}"
    content = resp.content.decode('utf-8','ignore')
    return False, f"HTTP {resp.status_code}: {content[:200]}"
test('C', 'C1', 'Offline Sale (Cash)', c1_offline_sale)

def c2_stock_after():
    if not PIDS: return False, "No products"
    resp = client.get(f'/api/products/{PIDS[0]}/')
    if resp.status_code == 200:
        stock = resp.json().get('stock', 0)
        return True, f"Stock now: {stock}"
    return False, f"HTTP {resp.status_code}"
test('C', 'C2', 'Stock After Sale', c2_stock_after)

def c3_offline_qris():
    if not PIDS: return False, "No products"
    pid = PIDS[1] if len(PIDS) > 1 else PIDS[0]
    resp = client.post('/api/orders/offline-sale/', {
        'product': pid, 'quantity': 2,
        'buyer_name': 'Siti', 'payment_method': 'qris'
    }, format='json')
    ok = resp.status_code == 201
    if ok:
        return True, f"HTTP 201 — QRIS sale OK"
    content = resp.content.decode('utf-8','ignore')
    return False, f"HTTP {resp.status_code}: {content[:200]}"
test('C', 'C3', 'Offline Sale (QRIS)', c3_offline_qris)

def c4_oversell():
    if not PIDS: return False, "No products"
    resp = client.post('/api/orders/offline-sale/', {
        'product': PIDS[0], 'quantity': 9999, 'payment_method': 'cash'
    }, format='json')
    # Harus ditolak — stok tidak cukup
    if resp.status_code in (400, 403):
        return True, f"Correctly rejected! HTTP {resp.status_code}"
    return False, f"Expected 400, got: HTTP {resp.status_code}"
test('C', 'C4', 'Over-sell Rejection', c4_oversell)

def c5_list_offline():
    resp = client.get('/api/orders/offline-sales/')
    if resp.status_code == 200:
        d = resp.json()
        sales = d if isinstance(d, list) else d.get('results', [])
        return True, f"{len(sales)} sales recorded"
    return False, f"HTTP {resp.status_code}: {resp.content.decode('utf-8','ignore')[:100]}"
test('C', 'C5', 'List Offline Sales', c5_list_offline)

# ── MANUAL STOCK EDIT ──
print("\n" + "─" * 70)
print("  FLOW D: MANUAL STOCK ADJUSTMENT")
print("─" * 70)

def d1_restock():
    if not PIDS: return False, "No products"
    resp = client.patch(f'/api/products/{PIDS[0]}/manage/', {
        'stock': 100, 'price': 16000
    }, format='json')
    if resp.status_code == 200:
        d = resp.json()
        return True, f"Stock: {d.get('stock','?')}, Price: {d.get('price','?')}"
    return False, f"HTTP {resp.status_code}"
test('D', 'D1', 'Restock Product', d1_restock)

def d2_verify_restock():
    if not PIDS: return False, "No products"
    resp = client.get(f'/api/products/{PIDS[0]}/')
    if resp.status_code == 200:
        stock = int(resp.json().get('stock', 0))
        return stock >= 50, f"Stock after restock: {stock}"
    return False, f"HTTP {resp.status_code}"
test('D', 'D2', 'Verify Restock', d2_verify_restock)

# ── SUMMARY ──
print("\n" + "=" * 70)
print("  HASIL TEST SELLER + OFFLINE PURCHASE")
print("=" * 70)

passed = sum(1 for r in results if r[3])
failed = sum(1 for r in results if not r[3])
total = len(results)
pct = passed / total * 100 if total else 0
print(f"\n  Total: {total} | ✅ PASS: {passed} | ❌ FAIL: {failed} | Score: {pct:.0f}%\n")

for r in results:
    s = "✅" if r[3] else "❌"
    print(f"  {s} | {r[0]}.{r[1]:3s} | {r[2][:35]:35s} | {r[4][:100]}")

# Cleanup
try:
    User.objects.filter(email=EMAIL).delete()
    print(f"\n  🧹 Cleaned up {EMAIL}")
except:
    pass

print(f"\n{'='*70}")
print(f"  TEST SELESAI")
print(f"{'='*70}")

sys.exit(1 if failed > 0 else 0)
