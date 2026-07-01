#!/usr/bin/env python3
"""Warungio Test — Buyer Full Flow (Register → Produk → Cart → Checkout → Payment + Admin Fee)"""
import os, django, uuid, random, sys, json

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
os.environ['CELERY_ENABLED'] = 'false'
os.environ['SECURE_SSL_REDIRECT'] = 'False'
os.environ['SESSION_COOKIE_SECURE'] = 'False'
os.environ['CSRF_COOKIE_SECURE'] = 'False'
os.environ['DJANGO_DEBUG'] = 'True'

django.setup()

from django.conf import settings
settings.DEBUG = True
settings.SECURE_SSL_REDIRECT = False
settings.ALLOWED_HOSTS = ['*']

from django.db import connection
from rest_framework.test import APIClient
from accounts.models import User, OTP
from stores.models import Store
from products.models import Product, Category
from orders.models import Order, Cart

client = APIClient()
results = []
uid = str(uuid.uuid4())[:6]

# ── Create seller & product first, then test buyer flow ──
SELLER_EMAIL = f"seller_{uid}@warungio.test"
BUYER_EMAIL = f"buyer_{uid}@warungio.test"
PASSWORD = 'Test@123456'
SELLER_PHONE = f"081234{random.randint(100000,999999)}"
BUYER_PHONE = f"081234{random.randint(100000,999999)}"

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
print("  WARUNGIO — BUYER FULL FLOW TEST")
print("="*70)

# ── PRE: DB Check ──
print("\n" + "─"*70)
print("  PRE-FLIGHT")
print("─"*70)

def pre_01():
    with connection.cursor() as c:
        c.execute("SELECT COUNT(*) FROM django_migrations")
        return True, f"{c.fetchone()[0]} migrations"
test('PRE', 'P0', 'Migrations', pre_01)

# ═══════════════════════════════════════════════════════════
# STEP 1: Register & setup SELLER (to have products)
# ═══════════════════════════════════════════════════════════
print("\n" + "─"*70)
print("  SETUP: Create Seller + Store + Products")
print("─"*70)

TOKEN_SELLER = ""
SID = None
PID = None

def s1_register():
    global TOKEN_SELLER
    r = client.post('/api/auth/register/', {
        'username': f's_{uid}', 'email': SELLER_EMAIL, 'password': PASSWORD,
        'password2': PASSWORD, 'full_name': 'Test Seller', 'phone': SELLER_PHONE,
        'role': 'seller'
    }, format='json')
    if r.status_code in (200,201):
        otp = r.json().get('otp_code','')
        # Verify OTP
        client.post('/api/auth/otp/verify/', {'email': SELLER_EMAIL, 'otp_code': otp}, format='json')
        # Login
        r2 = client.post('/api/auth/login/', {'email': SELLER_EMAIL, 'password': PASSWORD}, format='json')
        if r2.status_code == 200:
            TOKEN_SELLER = r2.json().get('access','')
            client.credentials(HTTP_AUTHORIZATION=f'Bearer {TOKEN_SELLER}')
            return True, "Seller registered & logged in"
    return False, f"Register failed: HTTP {r.status_code}"
test('SETUP', 'S1', 'Register Seller', s1_register)

def s2_store():
    global SID
    r = client.post('/api/stores/create/', {
        'store_name': f'Toko {uid}', 'description': 'Test store',
        'address': 'Jl. Test', 'city': 'Jakarta', 'province': 'DKI'
    }, format='json')
    if r.status_code in (200,201):
        r2 = client.get('/api/stores/my-store/')
        SID = r2.json().get('id') if r2.status_code == 200 else None
        return True, f"Store ID: {SID}"
    return False, f"HTTP {r.status_code}"
test('SETUP', 'S2', 'Create Store', s2_store)

def s3_products():
    global PID
    r = client.post('/api/products/create/', {
        'product_name': f'Beras {uid}', 'price': 15000, 'stock': 100,
        'unit': 'kg', 'product_status': 'fresh'
    }, format='json')
    if r.status_code in (200,201):
        r2 = client.get('/api/products/my-products/')
        items = r2.json().get('results', []) if r2.status_code == 200 else []
        PID = items[0]['id'] if items else None
        return True, f"Product ID: {PID}"
    return False, f"HTTP {r.status_code}: {r.content.decode()[:100]}"
test('SETUP', 'S3', 'Create Product', s3_products)

# ═══════════════════════════════════════════════════════════
# STEP 2: BUYER FLOW
# ═══════════════════════════════════════════════════════════
print("\n" + "─"*70)
print("  FLOW A: BUYER REGISTRATION & AUTH")
print("─"*70)

TOKEN_BUYER = ""
OTP_CODE = ""

def a1_register():
    global OTP_CODE
    r = client.post('/api/auth/register/', {
        'username': f'b_{uid}', 'email': BUYER_EMAIL, 'password': PASSWORD,
        'password2': PASSWORD, 'full_name': 'Test Buyer', 'phone': BUYER_PHONE,
        'role': 'buyer'
    }, format='json')
    if r.status_code in (200,201):
        OTP_CODE = r.json().get('otp_code','')
        return True, f"Buyer registered! OTP: {OTP_CODE}"
    return False, f"HTTP {r.status_code}"
test('A', 'A1', 'Register Buyer', a1_register)

def a2_verify():
    r = client.post('/api/auth/otp/verify/', {
        'email': BUYER_EMAIL, 'otp_code': OTP_CODE, 'purpose': 'registration'
    }, format='json')
    return r.status_code == 200, f"OTP Verify: HTTP {r.status_code}"
test('A', 'A2', 'Verify OTP', a2_verify)

def a3_login():
    global TOKEN_BUYER
    r = client.post('/api/auth/login/', {'email': BUYER_EMAIL, 'password': PASSWORD}, format='json')
    if r.status_code == 200:
        TOKEN_BUYER = r.json().get('access','')
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {TOKEN_BUYER}')
        return True, f"JWT: {TOKEN_BUYER[:30]}..."
    return False, f"HTTP {r.status_code}"
test('A', 'A3', 'Login JWT', a3_login)

def a4_profile():
    r = client.get('/api/auth/profile/')
    if r.status_code == 200:
        d = r.json()
        return True, f"Role: {d.get('role','?')} | Verified: {d.get('is_verified','?')}"
    return False, f"HTTP {r.status_code}"
test('A', 'A4', 'Profile Check', a4_profile)

# ═══════════════════════════════════════════════════════════
# FLOW B: BROWSE PRODUCTS
# ═══════════════════════════════════════════════════════════

print("\n" + "─"*70)
print("  FLOW B: BROWSE PRODUCTS")
print("─"*70)

def b1_list():
    r = client.get(f'/api/products/')
    if r.status_code == 200:
        d = r.json()
        count = len(d.get('results', []))
        return True, f"{count} products listed"
    return False, f"HTTP {r.status_code}"
test('B', 'B1', 'Browse Products', b1_list)

def b2_detail():
    if not PID: return False, "No product"
    r = client.get(f'/api/products/{PID}/')
    if r.status_code == 200:
        d = r.json()
        return True, f"{d.get('product_name','?')} — Rp {d.get('price','?')} | Stock: {d.get('stock','?')}"
    return False, f"HTTP {r.status_code}"
test('B', 'B2', 'Product Detail', b2_detail)

def b3_categories():
    r = client.get('/api/products/categories/')
    return r.status_code == 200, f"Categories OK"
test('B', 'B3', 'Categories', b3_categories)

# ═══════════════════════════════════════════════════════════
# FLOW C: CART & CHECKOUT
# ═══════════════════════════════════════════════════════════

print("\n" + "─"*70)
print("  FLOW C: CART & CHECKOUT")
print("─"*70)

OID = None

def c1_add_cart():
    if not PID: return False, "No product"
    r = client.post('/api/orders/cart/', {'product': PID, 'qty': 2}, format='json')
    return r.status_code in (200,201), f"Cart: HTTP {r.status_code}"
test('C', 'C1', 'Add to Cart', c1_add_cart)

def c2_cart_count():
    r = client.get('/api/orders/cart/count/')
    return r.status_code == 200, f"Count: {r.json()}"
test('C', 'C2', 'Cart Count', c2_cart_count)

def c3_cart_list():
    r = client.get('/api/orders/cart/')
    if r.status_code == 200:
        items = r.json().get('results', []) or []
        return True, f"{len(items)} items in cart"
    return False, f"HTTP {r.status_code}"
test('C', 'C3', 'Cart List', c3_cart_list)

def c4_shipping():
    r = client.get('/api/orders/shipping-methods/')
    items = r.json().get('results', []) if r.status_code == 200 else []
    return r.status_code == 200, f"{len(items)} shipping methods"
test('C', 'C4', 'Shipping Methods', c4_shipping)

def c5_create_order():
    global OID
    if not PID: return False, "No product"
    # Dapatkan cart_items ID dari keranjang user
    cart_r = client.get('/api/orders/cart/')
    if cart_r.status_code == 200:
        items = cart_r.json().get('results', []) or []
        cart_ids = [item['id'] for item in items if 'id' in item]
    else:
        cart_ids = []
    if not cart_ids:
        return False, "Cart is empty"
    r = client.post('/api/orders/create/', {
        'delivery_address': 'Jl. Pembeli No. 456, Jakarta',
        'recipient_name': 'Test Buyer',
        'recipient_phone': BUYER_PHONE,
        'payment_method': 'midtrans',
        'cart_items': cart_ids,
        'notes': 'Test order E2E'
    }, format='json')
    if r.status_code in (200,201):
        d = r.json()
        orders = d.get('orders', [])
        if orders:
            OID = orders[0].get('id')
        return True, f"Order created! ID: {OID}"
    return False, f"HTTP {r.status_code}: {r.content.decode()[:200]}"
test('C', 'C5', 'Create Order', c5_create_order)

def c6_order_detail():
    if not OID: return False, "No order"
    r = client.get(f'/api/orders/{OID}/')
    if r.status_code == 200:
        d = r.json()
        return True, f"Status: {d.get('order_status','?')} | Total: Rp {d.get('total_price','?')} | Admin Fee: Rp {d.get('admin_fee','?')}"
    return False, f"HTTP {r.status_code}"
test('C', 'C6', 'Order Detail (cek admin_fee)', c6_order_detail)

def c7_verify_admin_fee():
    """Verify the dual fee structure:
    
    Flow:
    - Buyer pays: total_price = subtotal + shipping - discount + admin_fee_buyer (Rp 1.500)
    - Seller receives: total_price - admin_fee (Rp 1.000) = seller net
    - Platform owner gets: admin_fee (Rp 1.000) for e-wallet 089667850425
    """
    if not OID: return False, "No order"
    r = client.get(f'/api/orders/{OID}/')
    if r.status_code == 200:
        d = r.json()
        admin_fee = float(d.get('admin_fee', 0))          # seller fee: Rp 1.000
        admin_fee_buyer = float(d.get('admin_fee_buyer', 0))  # buyer fee: Rp 1.500
        total = float(d.get('total_price', 0))
        subtotal = float(d.get('subtotal', 0))
        
        # Assertions
        has_admin_fee = admin_fee == 1000.0
        has_buyer_fee = admin_fee_buyer == 1500.0
        # total_price = subtotal + admin_fee_buyer
        total_correct = abs(total - (subtotal + admin_fee_buyer)) < 1
        seller_net = total - admin_fee
        
        all_ok = has_admin_fee and has_buyer_fee and total_correct
        return all_ok, \
            f"admin_fee={admin_fee}, admin_fee_buyer={admin_fee_buyer}, total={total}, subtotal={subtotal}, seller_net={seller_net} | Buyer fee +1500, Seller fee -1000"
    return False, f"HTTP {r.status_code}"
test('C', 'C7', 'Verify Admin Fee Rp 1.000', c7_verify_admin_fee)

def c8_my_orders():
    r = client.get('/api/orders/my-orders/')
    if r.status_code == 200:
        items = r.json().get('results', [])
        return True, f"{len(items)} orders"
    return False, f"HTTP {r.status_code}"
test('C', 'C8', 'My Orders', c8_my_orders)

# ═══════════════════════════════════════════════════════════
# FLOW D: PAYMENT CONFIG & METHODS
# ═══════════════════════════════════════════════════════════

print("\n" + "─"*70)
print("  FLOW D: PAYMENT")
print("─"*70)

def d1_methods():
    r = client.get('/api/payments/methods/')
    return r.status_code == 200, f"HTTP {r.status_code}"
test('D', 'D1', 'Payment Methods', d1_methods)

def d2_config():
    r = client.get('/api/payments/config/')
    if r.status_code == 200:
        d = r.json()
        return True, f"Client key: {d.get('client_key','?')[:10]}... | Prod: {d.get('is_production','?')}"
    return False, f"HTTP {r.status_code}"
test('D', 'D2', 'Payment Config', d2_config)

def d3_payment_status():
    if not OID: return False, "No order"
    r = client.get(f'/api/payments/status/{OID}/')
    return r.status_code == 200, f"Payment: {r.json()}"
test('D', 'D3', 'Payment Status', d3_payment_status)

# ═══════════════════════════════════════════════════════════
# FLOW E: HISTORY & SELLER VIEWS
# ═══════════════════════════════════════════════════════════

print("\n" + "─"*70)
print("  FLOW E: HISTORY & SELLER ORDERS")
print("─"*70)

def e1_history():
    r = client.get('/api/orders/history/')
    return r.status_code == 200, f"HTTP {r.status_code}"
test('E', 'E1', 'Order History', e1_history)

# Switch to seller to check seller orders
def e2_seller_orders():
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {TOKEN_SELLER}')
    r = client.get('/api/orders/seller/')
    if r.status_code == 200:
        items = r.json().get('results', [])
        return True, f"Seller sees {len(items)} orders"
    return False, f"HTTP {r.status_code}"
test('E', 'E2', 'Seller Orders View', e2_seller_orders)

# ═══════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════
print("\n" + "="*70)
print("  HASIL TEST BUYER FULL FLOW")
print("="*70)

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
    User.objects.filter(email=SELLER_EMAIL).delete()
    User.objects.filter(email=BUYER_EMAIL).delete()
    print(f"\n  🧹 Cleaned up test users")
except: pass

print(f"\n{'='*70}")
print(f"  TEST SELESAI")
print(f"{'='*70}")

sys.exit(1 if failed > 0 else 0)
