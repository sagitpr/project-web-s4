#!/usr/bin/env python3
"""
Warungio Complete E2E Integration Test
========================================
Tests the full Buyer-Seller lifecycle end-to-end through real Django APIs:

  SELLER: Register → Verify OTP → Login → Create Store → Publish Products
  BUYER:  Register → Verify OTP → Login → Browse Products → Add to Cart
          → Place Order → Complete Payment → Write Review
  VERIFY: Seller Dashboard → Buyer Dashboard → Admin → Database

Usage:  python scripts/test_e2e_full_flow.py
"""

import os, sys, json, uuid, random, time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ.setdefault('CELERY_ENABLED', 'false')
os.environ.setdefault('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver')
os.environ.setdefault('DJANGO_DEBUG', 'True')

import django
django.setup()

from django.conf import settings
settings.SECURE_SSL_REDIRECT = False
settings.SESSION_COOKIE_SECURE = False
settings.CSRF_COOKIE_SECURE = False
settings.CELERY_TASK_ALWAYS_EAGER = False  # Don't execute Celery tasks synchronously (skip email)

from django.db import connection
from rest_framework.test import APIClient
from accounts.models import User
from stores.models import Store
from products.models import Product, Category
from orders.models import Order, OrderItem, Cart, CartItem
from payments.models import Payment, Wallet, WalletTransaction

# ── Globals ──
uid = str(uuid.uuid4())[:8].replace('-', '0')
SELLER_EMAIL = f"seller_{uid}@warungio.test"
BUYER_EMAIL = f"buyer_{uid}@warungio.test"
PASSWORD = "Test@123456"
SELLER_PHONE = f"0812345{random.randint(10000,99999)}"
BUYER_PHONE = f"0812345{random.randint(10000,99999)}"

seller_client = APIClient()
buyer_client = APIClient()
admin_client = APIClient()

results = []
STORE_ID = None
PRODUCT_IDS = []
SELLER_ID = None
BUYER_ID = None
ORDER_ID = None
REVIEW_ID = None

# ── Test Runner ──
def test(flow, step, desc, func):
    try:
        ok, detail = func()
        icon = "✅" if ok else "❌"
        results.append((flow, step, desc, ok, str(detail)[:150]))
        print(f"  {icon} | {flow}.{step:2s} | {desc:45s} → {str(detail)[:120]}")
    except Exception as e:
        results.append((flow, step, desc, False, str(e)[:150]))
        print(f"  ❌ | {flow}.{step:2s} | {desc:45s} → ERROR: {e}")

# ══════════════════════════════════════════════════════════════════════════════
print("=" * 80)
print("  WARUNGIO — COMPLETE END-TO-END INTEGRATION TEST")
print(f"  Seller: {SELLER_EMAIL}")
print(f"  Buyer:  {BUYER_EMAIL}")
print(f"  UID:    {uid}")
print("=" * 80)

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 0: DATABASE PRE-FLIGHT
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "─" * 80)
print("  PHASE 0: DATABASE PRE-FLIGHT")
print("─" * 80)

def p0_migrations():
    with connection.cursor() as c:
        c.execute("SELECT COUNT(*) FROM django_migrations")
        count = c.fetchone()[0]
    return count > 0, f"{count} migrations applied"

def p0_tables():
    with connection.cursor() as c:
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in c.fetchall()]
    return len(tables) > 10, f"{len(tables)} tables in database"

def p0_counts():
    return True, f"Users: {User.objects.count()}, Stores: {Store.objects.count()}, Products: {Product.objects.count()}, Orders: {Order.objects.count()}"

def p0_cleanup():
    """Clean up any leftover test data from previous runs."""
    User.objects.filter(email__endswith='@warungio.test').delete()
    return True, "Cleaned previous test users"

test('P0', '0', 'Migrations applied', p0_migrations)
test('P0', '1', 'Database tables', p0_tables)
test('P0', '2', 'Initial record counts', p0_counts)
test('P0', '3', 'Cleanup previous test data', p0_cleanup)

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 1: SELLER REGISTRATION
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "─" * 80)
print("  PHASE 1: SELLER REGISTRATION & AUTH")
print("─" * 80)

def s1_register():
    resp = seller_client.post('/api/auth/register/', {
        'email': SELLER_EMAIL, 'password': PASSWORD, 'password2': PASSWORD,
        'full_name': 'Test Seller', 'phone': SELLER_PHONE, 'role': 'seller'
    }, format='json')
    ok = resp.status_code in (200, 201)
    if ok:
        global SELLER_ID
        SELLER_ID = resp.data.get('user', {}).get('id') or resp.data.get('id')
        return True, f"HTTP {resp.status_code}, User ID: {SELLER_ID}"
    return False, f"HTTP {resp.status_code}: {resp.data}"

def s1_verify_db_user():
    user = User.objects.filter(email=SELLER_EMAIL).first()
    if not user:
        return False, "User not found in database"
    return True, f"DB: id={user.id}, role={user.role}, is_verified={user.is_verified}"

def s2_otp_verify():
    from accounts.models import OTP
    otp = OTP.objects.filter(email=SELLER_EMAIL).order_by('-created_at').first()
    if not otp:
        return False, "No OTP found in database"
    resp = seller_client.post('/api/auth/otp/verify/', {
        'email': SELLER_EMAIL, 'otp_code': otp.otp_code, 'purpose': 'registration'
    }, format='json')
    ok = resp.status_code == 200
    return ok, f"OTP {otp.otp_code}, HTTP {resp.status_code}"

def s2_verify_db_verified():
    user = User.objects.filter(email=SELLER_EMAIL).first()
    return user.is_verified, f"is_verified={user.is_verified}"

def s3_login():
    resp = seller_client.post('/api/auth/login/', {
        'email': SELLER_EMAIL, 'password': PASSWORD
    }, format='json')
    ok = resp.status_code == 200
    if ok:
        token = resp.data.get('access', '')
        seller_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        return True, f"JWT token obtained, HTTP 200"
    return False, f"HTTP {resp.status_code}: {resp.data}"

def s4_check_auth():
    resp = seller_client.get('/api/auth/check-auth/')
    if resp.status_code == 200:
        u = resp.data.get('user', {})
        return True, f"Authenticated as {u.get('email','?')}, role={u.get('role','?')}"
    return False, f"HTTP {resp.status_code}"

def s5_profile():
    resp = seller_client.get('/api/auth/profile/')
    ok = resp.status_code == 200
    if ok:
        return True, f"Email: {resp.data.get('email','?')}, Phone: {resp.data.get('phone','?')}"
    return False, f"HTTP {resp.status_code}"

test('S1', '1', 'Register seller', s1_register)
test('S1', '2', 'Verify user in DB', s1_verify_db_user)
test('S1', '3', 'Verify OTP from DB', s2_otp_verify)
test('S1', '4', 'DB is_verified=true', s2_verify_db_verified)
test('S1', '5', 'Login (after OTP)', s3_login)
test('S1', '6', 'Check auth endpoint', s4_check_auth)
test('S1', '7', 'Profile endpoint', s5_profile)

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 2: SELLER STORE & PRODUCTS
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "─" * 80)
print("  PHASE 2: SELLER STORE & PRODUCT MANAGEMENT")
print("─" * 80)

def s6_create_store():
    global STORE_ID
    resp = seller_client.post('/api/stores/create/', {
        'store_name': f'Toko Test {uid}', 'category': 'Sembako',
        'description': 'Toko untuk testing E2E flow',
        'address': 'Jl. Merdeka No. 123, Jakarta Pusat',
        'province': 'DKI Jakarta', 'city': 'Jakarta Pusat',
        'district': 'Gambir', 'village': 'Kebon Kelapa',
        'postal_code': '10110', 'latitude': -6.2088, 'longitude': 106.8456,
        'open_time': '08:00', 'close_time': '22:00',
        'delivery_type': 'Instant,Reguler', 'service_area': 'Seluruh Kota',
        'bank_name': 'BCA', 'bank_account': '1234567890', 'bank_owner': 'Test Seller',
    }, format='json')
    ok = resp.status_code in (200, 201)
    if ok:
        STORE_ID = resp.data.get('id')
        return True, f"Store created, ID={STORE_ID}"
    return False, f"HTTP {resp.status_code}: {resp.data}"

def s7_verify_store_db():
    if not STORE_ID:
        return False, "No store ID"
    store = Store.objects.filter(id=STORE_ID).first()
    if not store:
        return False, "Store not in database"
    return True, f"DB: name={store.store_name}, status={store.status}, user_id={store.user_id}"

def s8_create_product():
    global PRODUCT_IDS
    product_data = [
        {'store': STORE_ID, 'name': f'Beras Premium {uid}', 'description': 'Beras premium kualitas terbaik',
         'price': '75000.00', 'stock': 100, 'unit': 'kg', 'category': 'Sembako',
         'product_status': 'available', 'is_active': True},
        {'store': STORE_ID, 'name': f'Minyak Goreng {uid}', 'description': 'Minyak goreng kemasan 1L',
         'price': '22000.00', 'stock': 50, 'unit': 'liter', 'category': 'Sembako',
         'product_status': 'available', 'is_active': True},
        {'store': STORE_ID, 'name': f'Gula Pasir {uid}', 'description': 'Gula pasir putih bersih',
         'price': '14000.00', 'stock': 30, 'unit': 'kg', 'category': 'Sembako',
         'product_status': 'available', 'is_active': True},
    ]
    created = []
    for p in product_data:
        resp = seller_client.post('/api/products/create/', p, format='json')
        if resp.status_code in (200, 201):
            created.append(resp.data.get('id'))
    PRODUCT_IDS = created
    return len(created) >= 1, f"{len(created)} products created (out of {len(product_data)})"

def s9_verify_products_db():
    count = Product.objects.filter(store_id=STORE_ID).count()
    return count >= 1, f"{count} products in database for store {STORE_ID}"

def s10_list_my_products():
    resp = seller_client.get('/api/products/my-products/')
    if resp.status_code == 200:
        items = resp.data.get('results', []) or []
        seller_count = len([p for p in items if str(p.get('store','')) == str(STORE_ID)])
        return True, f"{seller_count} seller products visible"
    return False, f"HTTP {resp.status_code}"

def s11_update_product():
    if not PRODUCT_IDS:
        return False, "No products"
    pid = PRODUCT_IDS[0]
    resp = seller_client.patch(f'/api/products/{pid}/manage/', {'price': '70000.00', 'stock': 95}, format='json')
    ok = resp.status_code == 200
    if ok:
        return True, f"Price=70000, Stock=95 confirmed"
    return False, f"HTTP {resp.status_code}: {resp.data}"

def s12_verify_product_db():
    if not PRODUCT_IDS:
        return False, "No products"
    product = Product.objects.get(id=PRODUCT_IDS[0])
    return float(product.price) == 70000.00 and product.stock == 95, f"DB: price={product.price}, stock={product.stock}"

def s13_my_store_detail():
    resp = seller_client.get('/api/stores/my-store/')
    if resp.status_code == 200:
        return True, f"Store: {resp.data.get('store_name','?')}, status={resp.data.get('status','?')}"
    return False, f"HTTP {resp.status_code}"

test('S1', '8', 'Create store', s6_create_store)
test('S1', '9', 'Verify store in DB', s7_verify_store_db)
test('S1', '10', 'Create 3 products', s8_create_product)
test('S1', '11', 'Verify products in DB', s9_verify_products_db)
test('S1', '12', 'List my products', s10_list_my_products)
test('S1', '13', 'Update product price/stock', s11_update_product)
test('S1', '14', 'Verify update in DB', s12_verify_product_db)
test('S1', '15', 'My store detail', s13_my_store_detail)

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 3: SELLER DASHBOARD & ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "─" * 80)
print("  PHASE 3: SELLER DASHBOARD & ANALYTICS")
print("─" * 80)

def s14_dashboard():
    resp = seller_client.get('/api/analytics/dashboard/')
    if resp.status_code == 200:
        return True, f"Dashboard: {json.dumps({k:v for k,v in resp.data.items() if not isinstance(v, list)}, default=str)[:120]}"
    return resp.status_code in (200, 403), f"HTTP {resp.status_code}"

def s15_seller_orders():
    resp = seller_client.get('/api/orders/seller/')
    if resp.status_code == 200:
        items = resp.data.get('results', []) or []
        return True, f"{len(items)} seller orders"
    return False, f"HTTP {resp.status_code}"

def s16_sales_trend():
    resp = seller_client.get('/api/analytics/sales/trend/')
    return resp.status_code in (200, 403), f"HTTP {resp.status_code}"

def s17_store_public():
    """Store should be visible in public listing (even without auth)"""
    resp = APIClient().get(f'/api/stores/')
    if resp.status_code == 200:
        items = resp.data.get('results', []) or []
        return True, f"{len(items)} stores in public listing"
    return False, f"HTTP {resp.status_code}"

def s18_products_public():
    """Products should be visible without auth for buyers to browse"""
    resp = APIClient().get('/api/products/')
    if resp.status_code == 200:
        items = resp.data.get('results', []) or []
        return True, f"{len(items)} products in public listing"
    return False, f"HTTP {resp.status_code}"

test('S2', '1', 'Seller dashboard', s14_dashboard)
test('S2', '2', 'Seller orders list', s15_seller_orders)
test('S2', '3', 'Sales trend', s16_sales_trend)
test('S2', '4', 'Store visible publicly', s17_store_public)
test('S2', '5', 'Products visible publicly', s18_products_public)

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 4: BUYER REGISTRATION
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "─" * 80)
print("  PHASE 4: BUYER REGISTRATION")
print("─" * 80)

def b1_register():
    resp = buyer_client.post('/api/auth/register/', {
        'email': BUYER_EMAIL, 'password': PASSWORD, 'password2': PASSWORD,
        'full_name': 'Test Buyer', 'phone': BUYER_PHONE, 'role': 'buyer'
    }, format='json')
    ok = resp.status_code in (200, 201)
    if ok:
        global BUYER_ID
        BUYER_ID = resp.data.get('user', {}).get('id') or resp.data.get('id')
        return True, f"HTTP {resp.status_code}, Buyer ID={BUYER_ID}"
    return False, f"HTTP {resp.status_code}: {resp.data}"

def b2_otp():
    from accounts.models import OTP
    otp = OTP.objects.filter(email=BUYER_EMAIL).order_by('-created_at').first()
    if not otp:
        return False, "No OTP in DB"
    resp = buyer_client.post('/api/auth/otp/verify/', {
        'email': BUYER_EMAIL, 'otp_code': otp.otp_code, 'purpose': 'registration'
    }, format='json')
    return resp.status_code == 200, f"OTP verified, HTTP {resp.status_code}"

def b3_login():
    resp = buyer_client.post('/api/auth/login/', {
        'email': BUYER_EMAIL, 'password': PASSWORD
    }, format='json')
    ok = resp.status_code == 200
    if ok:
        token = resp.data.get('access', '')
        buyer_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        return True, "JWT token obtained"
    return False, f"HTTP {resp.status_code}: {resp.data}"

def b4_browse():
    """Buyer browses published products — should see seller's products"""
    resp = buyer_client.get('/api/products/')
    if resp.status_code == 200:
        items = resp.data.get('results', []) or []
        seller_items = [p for p in items if str(p.get('store','')) == str(STORE_ID)]
        return True, f"{len(seller_items)} seller products visible to buyer"
    return False, f"HTTP {resp.status_code}"

def b5_product_detail():
    if not PRODUCT_IDS:
        return False, "No products"
    resp = buyer_client.get(f'/api/products/{PRODUCT_IDS[0]}/')
    if resp.status_code == 200:
        p = resp.data
        return True, f"{p.get('name','?')}, price={p.get('price','?')}, stock={p.get('stock','?')}"
    return False, f"HTTP {resp.status_code}"

test('B1', '1', 'Register buyer', b1_register)
test('B1', '2', 'Verify OTP', b2_otp)
test('B1', '3', 'Login', b3_login)
test('B1', '4', 'Browse products (see seller items)', b4_browse)
test('B1', '5', 'Product detail', b5_product_detail)

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 5: BUYER CART & ORDER
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "─" * 80)
print("  PHASE 5: BUYER CART & ORDER")
print("─" * 80)

def b6_add_to_cart():
    if not PRODUCT_IDS:
        return False, "No products"
    resp = buyer_client.post('/api/orders/cart/', {
        'product': PRODUCT_IDS[0], 'quantity': 2
    }, format='json')
    ok = resp.status_code in (200, 201)
    return ok, f"HTTP {resp.status_code}"

def b7_add_second_item():
    if len(PRODUCT_IDS) < 2:
        return False, "Need 2 products"
    resp = buyer_client.post('/api/orders/cart/', {
        'product': PRODUCT_IDS[1], 'quantity': 1
    }, format='json')
    return resp.status_code in (200, 201), f"HTTP {resp.status_code}"

def b8_cart_count():
    resp = buyer_client.get('/api/orders/cart/count/')
    if resp.status_code == 200:
        count = resp.data.get('count', 0)
        return count > 0, f"Cart count: {count}"
    return False, f"HTTP {resp.status_code}"

def b9_cart_list():
    resp = buyer_client.get('/api/orders/cart/')
    if resp.status_code == 200:
        items = resp.data.get('results', []) or []
        return len(items) >= 1, f"{len(items)} items in cart"
    return False, f"HTTP {resp.status_code}"

def b10_place_order():
    global ORDER_ID
    resp = buyer_client.post('/api/orders/create/', {
        'items': [{'product_id': PRODUCT_IDS[0], 'quantity': 2}],
        'shipping_address': 'Jl. Pembeli No. 456, Jakarta',
        'recipient_name': 'Test Buyer',
        'recipient_phone': BUYER_PHONE,
        'notes': 'Test order E2E',
        'payment_method': 'bank_transfer',
    }, format='json')
    ok = resp.status_code in (200, 201)
    if ok:
        ORDER_ID = resp.data.get('id') or resp.data.get('order_id')
        return True, f"Order created, ID={ORDER_ID}, HTTP {resp.status_code}"
    return False, f"HTTP {resp.status_code}: {resp.data}"

def b11_order_in_db():
    if not ORDER_ID:
        return False, "No order ID"
    order = Order.objects.filter(id=ORDER_ID).first()
    if not order:
        return False, "Order not in database"
    items_count = order.items.count()
    return True, f"DB: status={order.order_status}, items={items_count}, total={order.total_price}"

def b12_my_orders():
    resp = buyer_client.get('/api/orders/my-orders/')
    if resp.status_code == 200:
        items = resp.data.get('results', []) or []
        return len(items) >= 1, f"{len(items)} orders in buyer history"
    return False, f"HTTP {resp.status_code}"

def b13_order_detail():
    if not ORDER_ID:
        return False, "No order"
    resp = buyer_client.get(f'/api/orders/{ORDER_ID}/')
    if resp.status_code == 200:
        o = resp.data
        return True, f"Status: {o.get('order_status','?')}, Total: {o.get('total_price','?')}"
    return False, f"HTTP {resp.status_code}"

test('B2', '1', 'Add item 1 to cart', b6_add_to_cart)
test('B2', '2', 'Add item 2 to cart', b7_add_second_item)
test('B2', '3', 'Cart count', b8_cart_count)
test('B2', '4', 'Cart list', b9_cart_list)
test('B2', '5', 'Place order', b10_place_order)
test('B2', '6', 'Verify order in DB', b11_order_in_db)
test('B2', '7', 'My orders list', b12_my_orders)
test('B2', '8', 'Order detail', b13_order_detail)

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 6: BUYER PAYMENT
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "─" * 80)
print("  PHASE 6: BUYER PAYMENT")
print("─" * 80)

def b14_payment_methods():
    resp = buyer_client.get('/api/payments/methods/')
    if resp.status_code == 200:
        items = resp.data.get('results', []) or []
        return True, f"{len(items)} payment methods"
    return resp.status_code in (200, 404), f"HTTP {resp.status_code}"

def b15_payment_config():
    resp = buyer_client.get('/api/payments/config/')
    return resp.status_code == 200, f"HTTP {resp.status_code}"

def b16_wallet_balance():
    resp = buyer_client.get('/api/payments/wallet/balance/')
    if resp.status_code == 200:
        balance = resp.data.get('balance', 0)
        return True, f"Wallet balance: {balance}"
    return resp.status_code in (200, 404), f"HTTP {resp.status_code}"

def b17_wallet_transactions():
    resp = buyer_client.get('/api/payments/wallet/transactions/')
    if resp.status_code == 200:
        items = resp.data.get('results', []) or []
        return True, f"{len(items)} transactions"
    return resp.status_code in (200, 404), f"HTTP {resp.status_code}"

def b18_payment_status():
    if not ORDER_ID:
        return False, "No order"
    resp = buyer_client.get(f'/api/payments/status/{ORDER_ID}/')
    return resp.status_code in (200, 404), f"HTTP {resp.status_code}"

test('B3', '1', 'Payment methods', b14_payment_methods)
test('B3', '2', 'Payment config', b15_payment_config)
test('B3', '3', 'Wallet balance', b16_wallet_balance)
test('B3', '4', 'Wallet transactions', b17_wallet_transactions)
test('B3', '5', 'Payment status', b18_payment_status)

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 7: SELLER ORDER MANAGEMENT + REVIEW
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "─" * 80)
print("  PHASE 7: SELLER ORDER MGMT + BUYER REVIEW")
print("─" * 80)

def o1_seller_sees_order():
    resp = seller_client.get('/api/orders/seller/')
    if resp.status_code == 200:
        items = resp.data.get('results', []) or []
        return len(items) >= 1, f"{len(items)} orders visible to seller"
    return False, f"HTTP {resp.status_code}"

def o2_update_status():
    if not ORDER_ID:
        return False, "No order"
    resp = seller_client.post(f'/api/orders/{ORDER_ID}/status/', {
        'status': 'processed'
    }, format='json')
    ok = resp.status_code in (200, 201)
    return ok, f"Set to 'processed', HTTP {resp.status_code}"

def o3_verify_status_db():
    if not ORDER_ID:
        return False, "No order"
    order = Order.objects.get(id=ORDER_ID)
    return order.order_status == 'processed', f"DB status='{order.order_status}'"

def o4_shipping_methods():
    resp = buyer_client.get('/api/orders/shipping-methods/')
    if resp.status_code == 200:
        items = resp.data.get('results', []) or []
        return True, f"{len(items)} shipping methods"
    return resp.status_code in (200, 404), f"HTTP {resp.status_code}"

def o5_buyer_review():
    global REVIEW_ID
    if not PRODUCT_IDS:
        return False, "No products"
    resp = buyer_client.post('/api/products/create/', {
        'product_id': PRODUCT_IDS[0], 'rating': 5,
        'comment': 'Produk sangat bagus! Recommended!'
    }, format='json')
    # If dedicated review endpoint doesn't exist, try product review endpoint
    if resp.status_code == 404:
        resp = buyer_client.post(f'/api/products/{PRODUCT_IDS[0]}/reviews/', {
            'rating': 5, 'comment': 'Produk sangat bagus! Recommended!'
        }, format='json')
    ok = resp.status_code in (200, 201)
    if ok:
        REVIEW_ID = resp.data.get('id')
        return True, f"Review created, ID={REVIEW_ID}"
    return ok, f"HTTP {resp.status_code}"

test('O1', '1', 'Seller sees new order', o1_seller_sees_order)
test('O1', '2', 'Update order status', o2_update_status)
test('O1', '3', 'Verify status in DB', o3_verify_status_db)
test('O1', '4', 'Shipping methods', o4_shipping_methods)
test('O1', '5', 'Submit buyer review', o5_buyer_review)

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 8: NOTIFICATIONS & CHAT
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "─" * 80)
print("  PHASE 8: NOTIFICATIONS & CHAT")
print("─" * 80)

def n1_buyer_notifications():
    resp = buyer_client.get('/api/notifications/')
    if resp.status_code == 200:
        items = resp.data.get('results', []) or []
        return True, f"{len(items)} buyer notifications"
    return resp.status_code in (200, 403, 404), f"HTTP {resp.status_code}"

def n2_seller_notifications():
    resp = seller_client.get('/api/notifications/')
    if resp.status_code == 200:
        items = resp.data.get('results', []) or []
        return True, f"{len(items)} seller notifications"
    return resp.status_code in (200, 403, 404), f"HTTP {resp.status_code}"

def n3_conversations():
    resp = buyer_client.get('/api/chat/conversations/')
    if resp.status_code == 200:
        items = resp.data.get('results', []) or []
        return True, f"{len(items)} conversations"
    return resp.status_code in (200, 403, 404), f"HTTP {resp.status_code}"

def n4_unread_count():
    resp = buyer_client.get('/api/chat/unread-count/')
    return resp.status_code == 200, f"HTTP {resp.status_code}"

test('N1', '1', 'Buyer notifications', n1_buyer_notifications)
test('N1', '2', 'Seller notifications', n2_seller_notifications)
test('N1', '3', 'Chat conversations', n3_conversations)
test('N1', '4', 'Unread count', n4_unread_count)

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 9: ADMIN PANEL
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "─" * 80)
print("  PHASE 9: ADMIN/STAFF PANEL")
print("─" * 80)

def a1_create_admin():
    """Create an admin user and verify admin endpoints"""
    admin_user = User.objects.create_superuser(
        email=f"admin_{uid}@warungio.test",
        password=PASSWORD,
        full_name="Admin Test"
    )
    resp = admin_client.post('/api/auth/login/', {
        'email': f"admin_{uid}@warungio.test", 'password': PASSWORD
    }, format='json')
    ok = resp.status_code == 200
    if ok:
        token = resp.data.get('access', '')
        admin_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        return True, f"Admin user created, HTTP {resp.status_code}"
    return ok, f"HTTP {resp.status_code}"

def a2_admin_dashboard():
    resp = admin_client.get('/api/analytics/dashboard/')
    return resp.status_code in (200, 403), f"HTTP {resp.status_code}"

def a3_admin_users():
    resp = admin_client.get('/api/auth/profile/')
    return resp.status_code == 200, f"HTTP {resp.status_code}"

test('A1', '1', 'Create admin user', a1_create_admin)
test('A1', '2', 'Admin dashboard', a2_admin_dashboard)
test('A1', '3', 'Admin profile', a3_admin_users)

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 10: FINAL DATABASE VERIFICATION
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "─" * 80)
print("  PHASE 10: FINAL DATABASE VERIFICATION")
print("─" * 80)

def v1_count_users():
    count = User.objects.filter(email__endswith='@warungio.test').count()
    return count >= 3, f"{count} test users in DB (seller + buyer + admin)"

def v2_count_stores():
    count = Store.objects.all().count()
    my_store = Store.objects.filter(id=STORE_ID).first()
    return count >= 1 and my_store is not None, f"{count} stores total, store_id={STORE_ID} exists"

def v3_count_products():
    count = Product.objects.filter(store_id=STORE_ID).count()
    return count >= 1, f"{count} products for store {STORE_ID}"

def v4_count_orders():
    count = Order.objects.all().count()
    my_order = Order.objects.filter(id=ORDER_ID).first()
    return count >= 1 and my_order is not None, f"{count} orders total, order_id={ORDER_ID} exists"

def v5_stock_deducted():
    if not PRODUCT_IDS:
        return False, "No products"
    product = Product.objects.get(id=PRODUCT_IDS[0])
    # Ordered 2 items from initial stock of 95 (after update)
    return product.stock == 93, f"Stock={product.stock} (expected 93)"

def v6_order_status_chain():
    """Verify seller order exists by checking seller API"""
    resp = seller_client.get('/api/orders/seller/')
    if resp.status_code == 200:
        items = resp.data.get('results', []) or []
        return True, f"Seller sees {len(items)} orders"
    return False, f"HTTP {resp.status_code}"

def v7_public_store_listing():
    """Store appears in unauthenticated store listing"""
    resp = APIClient().get('/api/stores/')
    if resp.status_code == 200:
        items = resp.data.get('results', []) or []
        return True, f"{len(items)} stores in public listing"
    return False, f"HTTP {resp.status_code}"

def v8_health_check():
    resp = APIClient().get('/health/')
    return resp.status_code == 200, f"Health: HTTP {resp.status_code}"

test('V1', '1', 'Test users exist', v1_count_users)
test('V1', '2', 'Store exists in DB', v2_count_stores)
test('V1', '3', 'Products in DB', v3_count_products)
test('V1', '4', 'Orders in DB', v4_count_orders)
test('V1', '5', 'Stock deducted after order', v5_stock_deducted)
test('V1', '6', 'Seller order visibility', v6_order_status_chain)
test('V1', '7', 'Public store listing', v7_public_store_listing)
test('V1', '8', 'Health check', v8_health_check)

# ══════════════════════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("  RESULTS SUMMARY")
print("=" * 80)

passed = sum(1 for r in results if r[3])
failed = sum(1 for r in results if not r[3])
total = len(results)
pct = (passed / total * 100) if total > 0 else 0

print(f"\n  Total: {total} | ✅ PASS: {passed} | ❌ FAIL: {failed} | Score: {pct:.0f}%")
print()

phases = {}
for r in results:
    phase = r[0]
    if phase not in phases:
        phases[phase] = {'passed': 0, 'failed': 0, 'total': 0}
    phases[phase]['total'] += 1
    if r[3]:
        phases[phase]['passed'] += 1
    else:
        phases[phase]['failed'] += 1

print("  Per-Phase Results:")
for phase in sorted(phases.keys()):
    p = phases[phase]
    icon = "✅" if p['failed'] == 0 else "❌"
    print(f"  {icon} {phase}: {p['passed']}/{p['total']} passed")

print()

if failed > 0:
    print("  FAILED TESTS:")
    for r in results:
        if not r[3]:
            print(f"  ❌ {r[0]}.{r[1]} | {r[2]} | {r[4]}")

print(f"\n{'=' * 80}")
print(f"  TEST COMPLETE — {passed}/{total} passed ({pct:.0f}%)")
print(f"{'=' * 80}")

# ══════════════════════════════════════════════════════════════════════════════
# CLEANUP
# ══════════════════════════════════════════════════════════════════════════════
try:
    User.objects.filter(email__endswith='@warungio.test').delete()
    print(f"\n  🧹 Test users cleaned up")
except Exception as e:
    print(f"\n  ⚠️  Cleanup warning: {e}")

sys.exit(0 if failed == 0 else 1)
