#!/usr/bin/env python3
"""Warungio — Midtrans Production E2E Test"""
import os, django, uuid, random, sys, json, time

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
os.environ['SECURE_SSL_REDIRECT'] = 'False'
os.environ['SESSION_COOKIE_SECURE'] = 'False'
os.environ['CSRF_COOKIE_SECURE'] = 'False'
os.environ['DJANGO_DEBUG'] = 'True'
# ⚠️  JANGAN hardcode kredensial production!
# Set MIDTRANS_SERVER_KEY, MIDTRANS_CLIENT_KEY, MIDTRANS_MERCHANT_ID di .env
# atau export environment variable sebelum menjalankan test ini.
os.environ['MIDTRANS_SERVER_KEY'] = os.environ.get('MIDTRANS_SERVER_KEY', '')
os.environ['MIDTRANS_CLIENT_KEY'] = os.environ.get('MIDTRANS_CLIENT_KEY', '')
os.environ['MIDTRANS_MERCHANT_ID'] = os.environ.get('MIDTRANS_MERCHANT_ID', '')
os.environ['MIDTRANS_IS_PRODUCTION'] = 'True'

django.setup()

from django.conf import settings
settings.DEBUG = True
settings.SECURE_SSL_REDIRECT = False
settings.ALLOWED_HOSTS = ['*', 'testserver', 'localhost']
settings.MIDTRANS_IS_PRODUCTION = True
settings.MIDTRANS_SNAP_URL = 'https://app.midtrans.com/snap/v1/transactions'
# Baca kredensial dari env var (sudah di-set via os.environ di atas)
settings.MIDTRANS_SERVER_KEY = os.environ.get('MIDTRANS_SERVER_KEY', '')
settings.MIDTRANS_CLIENT_KEY = os.environ.get('MIDTRANS_CLIENT_KEY', '')
settings.MIDTRANS_MERCHANT_ID = os.environ.get('MIDTRANS_MERCHANT_ID', '')

from rest_framework.test import APIClient
from accounts.models import User
client = APIClient()
results = []
uid = str(uuid.uuid4())[:6]

SELLER_EMAIL = f"ms_{uid}@test.com"
BUYER_EMAIL = f"mb_{uid}@test.com"
PASSWORD = 'Test@123456'
SELLER_PHONE = f"0812{random.randint(100000,999999)}"
BUYER_PHONE = f"0812{random.randint(100000,999999)}"

TOKEN_SELLER = ""; TOKEN_BUYER = ""
SID = None; PID = None; OID = None
SNAP_TOKEN = None; TX_ORDER_ID = None

def test(flow, step, desc, func):
    try:
        ok, detail = func()
        results.append((flow, step, desc, ok, str(detail)[:150]))
        s = "✅" if ok else "❌"
        print(f"  {s} | {step}: {desc} -> {str(detail)[:120]}")
    except Exception as e:
        import traceback; traceback.print_exc()
        results.append((flow, step, desc, False, str(e)[:150]))
        print(f"  ❌ ERROR | {step}: {desc} -> {e}")

def hdrs(token=None):
    h = {'HTTP_HOST': 'localhost:8000', 'HTTP_REFERER': 'http://localhost:8000'}
    if token:
        h['HTTP_AUTHORIZATION'] = f'Bearer {token}'
    return h

print("=" * 70)
print("  WARUNGIO — MIDTRANS PRODUCTION E2E TEST")
print("=" * 70)

# ── STEP 1: SELLER SETUP ──
print("\n" + "─" * 70)
print("  STEP 1: SELLER SETUP")
print("─" * 70)

def s1_register():
    global TOKEN_SELLER
    r = client.post('/api/auth/register/', {
        'username': f'ms_{uid}', 'email': SELLER_EMAIL, 'password': PASSWORD,
        'password2': PASSWORD, 'full_name': 'Midtrans Seller', 'phone': SELLER_PHONE,
        'role': 'seller'
    }, format='json', **hdrs())
    if r.status_code in (200, 201):
        otp = r.json().get('otp_code', '')
        client.post('/api/auth/otp/verify/', {'email': SELLER_EMAIL, 'otp_code': otp}, format='json', **hdrs())
        r2 = client.post('/api/auth/login/', {'email': SELLER_EMAIL, 'password': PASSWORD}, format='json', **hdrs())
        if r2.status_code == 200:
            TOKEN_SELLER = r2.json().get('access', '')
            return True, "Seller registered & logged in"
    return False, f"HTTP {r.status_code}: {r.content.decode()[:100]}"
test('S1', 'S1', 'Register Seller', s1_register)

def s2_store():
    global SID
    client.credentials(**hdrs(TOKEN_SELLER))
    r = client.post('/api/stores/create/', {
        'store_name': f'Toko Mid {uid}', 'description': 'Test',
        'address': 'Jl. Test 1', 'city': 'Jakarta', 'province': 'DKI Jakarta'
    }, format='json')
    if r.status_code in (200, 201):
        r2 = client.get('/api/stores/my-store/', **hdrs(TOKEN_SELLER))
        SID = r2.json().get('id') if r2.status_code == 200 else None
        return True, f"Store ID: {SID}"
    return False, f"HTTP {r.status_code}"
test('S1', 'S2', 'Create Store', s2_store)

def s3_product():
    global PID
    r = client.post('/api/products/create/', {
        'product_name': f'Beras {uid}', 'price': 25000, 'stock': 50, 'unit': 'kg'
    }, format='json')
    if r.status_code in (200, 201):
        r2 = client.get('/api/products/my-products/')
        items = r2.json().get('results', []) if r2.status_code == 200 else []
        PID = items[0]['id'] if items else None
        return True, f"Product ID: {PID}, Price: 25000"
    return False, f"HTTP {r.status_code}"
test('S1', 'S3', 'Create Product', s3_product)

# ── STEP 2: BUYER CHECKOUT ──
print("\n" + "─" * 70)
print("  STEP 2: BUYER CHECKOUT")
print("─" * 70)

def b1_register():
    global OTP_CODE
    r = client.post('/api/auth/register/', {
        'username': f'mb_{uid}', 'email': BUYER_EMAIL, 'password': PASSWORD,
        'password2': PASSWORD, 'full_name': 'Midtrans Buyer', 'phone': BUYER_PHONE,
        'role': 'buyer'
    }, format='json', **hdrs())
    if r.status_code in (200, 201):
        OTP_CODE = r.json().get('otp_code', '')
        return True, "Buyer registered"
    return False, f"HTTP {r.status_code}"
test('S2', 'B1', 'Register Buyer', b1_register)

def b2_verify():
    r = client.post('/api/auth/otp/verify/', {
        'email': BUYER_EMAIL, 'otp_code': OTP_CODE, 'purpose': 'registration'
    }, format='json', **hdrs())
    return r.status_code == 200, f"OTP: HTTP {r.status_code}"
test('S2', 'B2', 'Verify OTP', b2_verify)

def b3_login():
    global TOKEN_BUYER
    r = client.post('/api/auth/login/', {'email': BUYER_EMAIL, 'password': PASSWORD}, format='json', **hdrs())
    if r.status_code == 200:
        TOKEN_BUYER = r.json().get('access', '')
        client.credentials(**hdrs(TOKEN_BUYER))
        return True, "Login OK"
    return False, f"HTTP {r.status_code}"
test('S2', 'B3', 'Login Buyer', b3_login)

def b4_config():
    r = client.get('/api/payments/config/')
    if r.status_code == 200:
        d = r.json()
        prod = d.get('is_production', False)
        snap = d.get('snap_url', '')
        return prod == True and 'app.midtrans.com' in snap, \
            f"Production={prod}, Snap={snap}"
    return False, f"HTTP {r.status_code}"
test('S2', 'B4', 'Payment Config (Production)', b4_config)

def b5_cart():
    if not PID: return False, "No product"
    r = client.post('/api/orders/cart/', {'product': PID, 'qty': 2}, format='json')
    return r.status_code in (200, 201), f"Cart: HTTP {r.status_code}"
test('S2', 'B5', 'Add to Cart (2x Rp 25.000)', b5_cart)

def b6_order():
    global OID
    cart_r = client.get('/api/orders/cart/')
    items = cart_r.json().get('results', []) if cart_r.status_code == 200 else []
    cart_ids = [i['id'] for i in items if 'id' in i]
    if not cart_ids: return False, "Cart empty"
    r = client.post('/api/orders/create/', {
        'delivery_address': 'Jl. Pembeli 456, Jakarta',
        'recipient_name': 'Midtrans Buyer',
        'recipient_phone': BUYER_PHONE,
        'payment_method': 'midtrans',
        'cart_items': cart_ids,
    }, format='json')
    if r.status_code in (200, 201):
        orders = r.json().get('orders', [])
        OID = orders[0].get('id') if orders else None
        return True, f"Order ID: {OID}"
    return False, f"HTTP {r.status_code}: {r.content.decode()[:200]}"
test('S2', 'B6', 'Create Order', b6_order)

def b7_verify_fees():
    if not OID: return False, "No order"
    r = client.get(f'/api/orders/{OID}/')
    if r.status_code == 200:
        d = r.json()
        af = float(d.get('admin_fee', 0))
        afb = float(d.get('admin_fee_buyer', 0))
        total = float(d.get('total_price', 0))
        sub = float(d.get('subtotal', 0))
        expected = sub + afb
        ok = (af == 1000 and afb == 1500 and abs(total - expected) < 1)
        return ok, f"total={total}, sub={sub}, fee_seller={af}, fee_buyer={afb}, expected={expected}"
    return False, f"HTTP {r.status_code}"
test('S2', 'B7', 'Verify Dual Fee (seller 1000, buyer 1500)', b7_verify_fees)

# ── STEP 3: MIDTRANS SNAP ──
print("\n" + "─" * 70)
print("  STEP 3: MIDTRANS SNAP TRANSACTION")
print("─" * 70)

def snap_create():
    global SNAP_TOKEN, TX_ORDER_ID
    if not OID: return False, "No order"
    r = client.post('/api/payments/create-snap/', {
        'order_id': OID, 'payment_method': 'bank_transfer', 'bank': 'bca'
    }, format='json')
    if r.status_code in (200, 201):
        d = r.json()
        SNAP_TOKEN = d.get('token', '')
        TX_ORDER_ID = d.get('transaction_id', '')
        print(f"    Snap Token: {SNAP_TOKEN[:40]}...")
        print(f"    TX Order ID: {TX_ORDER_ID}")
        print(f"    Redirect URL: {d.get('redirect_url', 'N/A')}")
        return bool(SNAP_TOKEN), f"Snap created! Token: {str(SNAP_TOKEN)[:30]}..."
    return False, f"HTTP {r.status_code}: {r.content.decode()[:300]}"
test('S3', 'M1', 'Create Snap Transaction', snap_create)

def snap_status():
    if not OID: return False, "No order"
    r = client.get(f'/api/payments/status/{OID}/')
    return r.status_code == 200, f"Status: {r.json()}"
test('S3', 'M2', 'Payment Status', snap_status)

def snap_verify_midtrans():
    """Verify transaction exists on Midtrans directly"""
    if not TX_ORDER_ID: return False, "No transaction"
    import base64, requests
    auth = base64.b64encode(f"{settings.MIDTRANS_SERVER_KEY}:".encode()).decode()
    headers = {'Authorization': f'Basic {auth}', 'Accept': 'application/json'}
    r = requests.get(f"https://api.midtrans.com/v2/{TX_ORDER_ID}/status", headers=headers, timeout=15)
    if r.status_code == 200:
        d = r.json()
        status = d.get('transaction_status', 'unknown')
        return True, f"Midtrans status: {status} | payment: {d.get('payment_type','?')} | amount: {d.get('gross_amount','?')}"
    return False, f"Midtrans API: HTTP {r.status_code}: {r.text[:200]}"
test('S3', 'M3', 'Verify Midtrans Transaction Status', snap_verify_midtrans)

# ── STEP 4: SELLER FINANCE ──
print("\n" + "─" * 70)
print("  STEP 4: SELLER FINANCE")
print("─" * 70)

def seller_finance():
    if not TOKEN_SELLER: return False, "No seller"
    client.credentials(**hdrs(TOKEN_SELLER))
    r = client.get('/api/payments/finance/summary/')
    if r.status_code == 200:
        d = r.json()
        print(f"    Gross: {d['total_income_gross']}, Net: {d['total_income_net']}, Admin Fees: {d['total_admin_fees']}")
        return True, f"Finance: net={d['total_income_net']}, admin_fees={d['total_admin_fees']}"
    return False, f"HTTP {r.status_code}"
test('S4', 'F1', 'Seller Finance Summary', seller_finance)

# ═══════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  RESULTS")
print("=" * 70)
passed = sum(1 for r in results if r[3])
failed = sum(1 for r in results if not r[3])
total = len(results)
pct = passed / total * 100 if total else 0
print(f"\n  Total: {total} | ✅ PASS: {passed} | ❌ FAIL: {failed} | Score: {pct:.0f}%\n")
for r in results:
    s = "✅" if r[3] else "❌"
    print(f"  {s} | {r[0]}.{r[1]:3s} | {r[2][:40]:40s} | {str(r[4])[:120]}")

# Cleanup
try:
    User.objects.filter(email__in=[SELLER_EMAIL, BUYER_EMAIL]).delete()
    print("\n  🧹 Cleaned up")
except: pass

sys.exit(1 if failed > 0 else 0)
