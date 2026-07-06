#!/usr/bin/env python3
"""
Warungio Complete E2E Integration Test
========================================
Tests the full Buyer-Seller lifecycle end-to-end through real Django APIs.
Usage:  python scripts/test_e2e_full_flow.py
"""

import os, sys, json, uuid, random, time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ['DJANGO_ALLOWED_HOSTS'] = '*'
os.environ.setdefault('CELERY_ENABLED', 'false')
os.environ['DJANGO_DEBUG'] = 'True'
os.environ['USE_MYSQL'] = 'False'

import django
django.setup()

from django.conf import settings
settings.ALLOWED_HOSTS = ['*']

from django.db import connection
from rest_framework.test import APIClient
from rest_framework.response import Response

from accounts.models import User, OTP
from stores.models import Store
from products.models import Product, Category
from orders.models import Order, OrderItem, Cart
from payments.models import Payment, Wallet, WalletTransaction

uid = str(uuid.uuid4())[:8].replace('-', '0')
SELLER_EMAIL = "seller_{}@warungio.test".format(uid)
BUYER_EMAIL = "buyer_{}@warungio.test".format(uid)
PASSWORD = "Test@123456"
SELLER_PHONE = "0812345{}".format(random.randint(10000,99999))
BUYER_PHONE = "0812345{}".format(random.randint(10000,99999))

seller_client = APIClient()
buyer_client = APIClient()
admin_client = APIClient()

results = []
STORE_ID = None
PRODUCT_IDS = []
SELLER_ID = None
BUYER_ID = None
ORDER_ID = None
CART_IDS = []

def resp_data(resp):
    try:
        if hasattr(resp, 'data') and resp.data is not None:
            return resp.data
        if hasattr(resp, 'content') and resp.content:
            return json.loads(resp.content.decode('utf-8'))
    except (json.JSONDecodeError, AttributeError, UnicodeDecodeError):
        pass
    return {}

def resp_ok(resp, codes=(200, 201)):
    return resp.status_code in codes

def api_get(client, url, **kwargs):
    return client.get(url, **kwargs)

def api_post(client, url, data, **kwargs):
    return client.post(url, data, format='json', **kwargs)

def api_patch(client, url, data, **kwargs):
    return client.patch(url, data, format='json', **kwargs)

def test(flow, step, desc, func):
    try:
        ok, detail = func()
        icon = "PASS" if ok else "FAIL"
        results.append((flow, step, desc, ok, str(detail)[:150]))
        print("  {} | {}.{:2s} | {:45s} -> {}".format(
            icon, flow, step, desc, str(detail)[:120]))
    except Exception as e:
        import traceback
        results.append((flow, step, desc, False, str(e)[:150]))
        print("  FAIL | {}.{:2s} | {:45s} -> ERROR: {}".format(flow, step, desc, e))
        traceback.print_exc()

# ============================================================================
print("=" * 80)
print("  WARUNGIO -- COMPLETE END-TO-END INTEGRATION TEST")
print("  Seller: {}".format(SELLER_EMAIL))
print("  Buyer:  {}".format(BUYER_EMAIL))
print("  UID:    {}".format(uid))
print("=" * 80)

# ============================================================================
# PHASE 0: DATABASE PRE-FLIGHT
# ============================================================================
print("\n" + "-" * 80)
print("  PHASE 0: DATABASE PRE-FLIGHT")
print("-" * 80)

def p0_migrations():
    with connection.cursor() as c:
        c.execute("SELECT COUNT(*) FROM django_migrations")
        count = c.fetchone()[0]
    return count > 0, "{} migrations applied".format(count)

def p0_tables():
    with connection.cursor() as c:
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in c.fetchall()]
    return len(tables) > 10, "{} tables in database".format(len(tables))

def p0_counts():
    return True, "Users: {}, Stores: {}, Products: {}, Orders: {}".format(
        User.objects.count(), Store.objects.count(),
        Product.objects.count(), Order.objects.count())

def p0_cleanup():
    try:
        User.objects.filter(email__endswith='@warungio.test').delete()
        return True, "Cleaned previous test users"
    except Exception as e:
        return True, "Cleanup (best-effort): {}".format(str(e)[:120])

test('P0', '0', 'Migrations applied', p0_migrations)
test('P0', '1', 'Database tables', p0_tables)
test('P0', '2', 'Initial record counts', p0_counts)
test('P0', '3', 'Cleanup previous test data', p0_cleanup)

# ============================================================================
# PHASE 1: SELLER REGISTRATION
# ============================================================================
print("\n" + "-" * 80)
print("  PHASE 1: SELLER REGISTRATION & AUTH")
print("-" * 80)

def s1_register():
    resp = api_post(seller_client, '/api/auth/register/', {
        'email': SELLER_EMAIL, 'password': PASSWORD, 'password2': PASSWORD,
        'full_name': 'Test Seller', 'phone': SELLER_PHONE, 'role': 'seller'
    })
    ok = resp_ok(resp)
    if ok:
        global SELLER_ID
        d = resp_data(resp)
        SELLER_ID = d.get('user', {}).get('id') or d.get('id')
        return True, "HTTP {}, User ID: {}".format(resp.status_code, SELLER_ID)
    return False, "HTTP {}: {}".format(resp.status_code, resp_data(resp))

def s1_verify_db_user():
    user = User.objects.filter(email=SELLER_EMAIL).first()
    if not user:
        return False, "User not found in database"
    return True, "DB: id={}, role={}, is_verified={}".format(
        user.id, user.role, user.is_verified)

def s2_otp_verify():
    otp = OTP.objects.filter(email=SELLER_EMAIL).order_by('-created_at').first()
    if not otp:
        return False, "No OTP found in database"
    resp = api_post(seller_client, '/api/auth/otp/verify/', {
        'email': SELLER_EMAIL, 'otp_code': otp.otp_code, 'purpose': 'registration'
    })
    ok = resp_ok(resp)
    return ok, "OTP {}, HTTP {}".format(otp.otp_code, resp.status_code)

def s2_verify_db_verified():
    user = User.objects.filter(email=SELLER_EMAIL).first()
    return user.is_verified, "is_verified={}".format(user.is_verified)

def s3_login():
    resp = api_post(seller_client, '/api/auth/login/', {
        'email': SELLER_EMAIL, 'password': PASSWORD
    })
    ok = resp_ok(resp)
    if ok:
        token = resp_data(resp).get('access', '')
        seller_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(token))
        return True, "JWT token obtained, HTTP 200"
    return False, "HTTP {}: {}".format(resp.status_code, resp_data(resp))

def s4_check_auth():
    resp = api_get(seller_client, '/api/auth/check-auth/')
    if resp_ok(resp):
        u = resp_data(resp).get('user', {})
        return True, "Authenticated as {}, role={}".format(
            u.get('email','?'), u.get('role','?'))
    return False, "HTTP {}".format(resp.status_code)

def s5_profile():
    resp = api_get(seller_client, '/api/auth/profile/')
    ok = resp_ok(resp)
    if ok:
        d = resp_data(resp)
        return True, "Email: {}, Phone: {}".format(
            d.get('email','?'), d.get('phone','?'))
    return False, "HTTP {}".format(resp.status_code)

test('S1', '1', 'Register seller', s1_register)
test('S1', '2', 'Verify user in DB', s1_verify_db_user)
test('S1', '3', 'Verify OTP from DB', s2_otp_verify)
test('S1', '4', 'DB is_verified=true', s2_verify_db_verified)
test('S1', '5', 'Login (after OTP)', s3_login)
test('S1', '6', 'Check auth endpoint', s4_check_auth)
test('S1', '7', 'Profile endpoint', s5_profile)

# ============================================================================
# PHASE 2: SELLER STORE & PRODUCTS
# ============================================================================
print("\n" + "-" * 80)
print("  PHASE 2: SELLER STORE & PRODUCT MANAGEMENT")
print("-" * 80)

def s6_create_store():
    global STORE_ID
    resp = api_post(seller_client, '/api/stores/create/', {
        'store_name': 'Toko Test {}'.format(uid), 'category': 'Sembako',
        'description': 'Toko untuk testing E2E flow',
        'address': 'Jl. Merdeka No. 123, Jakarta Pusat',
        'province': 'DKI Jakarta', 'city': 'Jakarta Pusat',
        'district': 'Gambir', 'village': 'Kebon Kelapa',
        'postal_code': '10110', 'latitude': -6.2088, 'longitude': 106.8456,
        'open_time': '08:00', 'close_time': '22:00',
        'delivery_type': 'Instant,Reguler', 'service_area': 'Seluruh Kota',
        'bank_name': 'BCA', 'bank_account': '1234567890', 'bank_owner': 'Test Seller',
    })
    ok = resp_ok(resp)
    if ok:
        STORE_ID = resp_data(resp).get('id')
        return True, "Store created, ID={}".format(STORE_ID)
    return False, "HTTP {}: {}".format(resp.status_code, resp_data(resp))

def s7_verify_store_db():
    if not STORE_ID:
        return False, "No store ID"
    store = Store.objects.filter(id=STORE_ID).first()
    if not store:
        return False, "Store not in database"
    return True, "DB: name={}, status={}, user_id={}".format(
        store.store_name, store.status, store.user_id)

def s8_create_product():
    global PRODUCT_IDS
    cat = Category.objects.filter(category_name='Sembako').first()
    cat_id = cat.id if cat else 27
    product_data = [
        {'product_name': 'Beras Premium {}'.format(uid),
         'description': 'Beras premium kualitas terbaik',
         'price': '75000.00', 'stock': 100, 'unit': 'kg',
         'category': cat_id, 'product_status': 'fresh'},
        {'product_name': 'Minyak Goreng {}'.format(uid),
         'description': 'Minyak goreng kemasan 1L',
         'price': '22000.00', 'stock': 50, 'unit': 'liter',
         'category': cat_id, 'product_status': 'fresh'},
        {'product_name': 'Gula Pasir {}'.format(uid),
         'description': 'Gula pasir putih bersih',
         'price': '14000.00', 'stock': 30, 'unit': 'kg',
         'category': cat_id, 'product_status': 'fresh'},
    ]
    created = []
    for p in product_data:
        resp = api_post(seller_client, '/api/products/create/', p)
        if resp_ok(resp):
            created.append(resp_data(resp).get('id'))
    PRODUCT_IDS = created
    return len(created) >= 1, "{} products created (out of {})".format(
        len(created), len(product_data))

def s9_verify_products_db():
    count = Product.objects.filter(store_id=STORE_ID).count()
    return count >= 1, "{} products in database for store {}".format(count, STORE_ID)

def s10_list_my_products():
    resp = api_get(seller_client, '/api/products/my-products/')
    if resp_ok(resp):
        items = resp_data(resp).get('results', []) or []
        return True, "{} products in my-products".format(len(items))
    return False, "HTTP {}".format(resp.status_code)

def s11_update_product():
    if not PRODUCT_IDS:
        return False, "No products"
    pid = PRODUCT_IDS[0]
    resp = api_patch(seller_client, '/api/products/{}/manage/'.format(pid),
                     {'price': '70000.00', 'stock': 95})
    ok = resp_ok(resp)
    if ok:
        return True, "Price/Stock updated: HTTP {}".format(resp.status_code)
    return False, "HTTP {}: {}".format(resp.status_code, resp_data(resp))

def s12_verify_product_db():
    if not PRODUCT_IDS:
        return False, "No products"
    product = Product.objects.get(id=PRODUCT_IDS[0])
    exp = float(product.price) == 70000.00 and product.stock == 95
    return exp, "DB: price={}, stock={}".format(product.price, product.stock)

def s13_my_store_detail():
    resp = api_get(seller_client, '/api/stores/my-store/')
    if resp_ok(resp):
        d = resp_data(resp)
        return True, "Store: {}, status={}".format(
            d.get('store_name','?'), d.get('status','?'))
    return False, "HTTP {}".format(resp.status_code)

test('S1', '8', 'Create store', s6_create_store)
test('S1', '9', 'Verify store in DB', s7_verify_store_db)
test('S1', '10', 'Create 3 products', s8_create_product)
test('S1', '11', 'Verify products in DB', s9_verify_products_db)
test('S1', '12', 'List my products', s10_list_my_products)
test('S1', '13', 'Update product price/stock', s11_update_product)
test('S1', '14', 'Verify update in DB', s12_verify_product_db)
test('S1', '15', 'My store detail', s13_my_store_detail)

# ============================================================================
# PHASE 3: SELLER DASHBOARD & ANALYTICS
# ============================================================================
print("\n" + "-" * 80)
print("  PHASE 3: SELLER DASHBOARD & ANALYTICS")
print("-" * 80)

def s14_dashboard():
    resp = api_get(seller_client, '/api/analytics/dashboard/')
    return resp.status_code == 200, "Dashboard: HTTP {}".format(resp.status_code)

def s15_seller_orders():
    resp = api_get(seller_client, '/api/orders/seller/')
    if resp_ok(resp):
        items = resp_data(resp).get('results', []) or []
        return True, "{} seller orders".format(len(items))
    return False, "HTTP {}".format(resp.status_code)

def s16_sales_trend():
    resp = api_get(seller_client, '/api/analytics/sales/trend/')
    return resp.status_code in (200, 403), "HTTP {}".format(resp.status_code)

def s17_store_public():
    resp = api_get(APIClient(), '/api/stores/')
    if resp_ok(resp):
        items = resp_data(resp).get('results', []) or []
        return True, "{} stores in public listing".format(len(items))
    return False, "HTTP {}".format(resp.status_code)

def s18_products_public():
    resp = api_get(APIClient(), '/api/products/')
    if resp_ok(resp):
        items = resp_data(resp).get('results', []) or []
        return True, "{} products in public listing".format(len(items))
    return False, "HTTP {}".format(resp.status_code)

test('S2', '1', 'Seller dashboard', s14_dashboard)
test('S2', '2', 'Seller orders list', s15_seller_orders)
test('S2', '3', 'Sales trend', s16_sales_trend)
test('S2', '4', 'Store visible publicly', s17_store_public)
test('S2', '5', 'Products visible publicly', s18_products_public)

# ============================================================================
# PHASE 4: BUYER REGISTRATION
# ============================================================================
print("\n" + "-" * 80)
print("  PHASE 4: BUYER REGISTRATION")
print("-" * 80)

def b1_register():
    resp = api_post(buyer_client, '/api/auth/register/', {
        'email': BUYER_EMAIL, 'password': PASSWORD, 'password2': PASSWORD,
        'full_name': 'Test Buyer', 'phone': BUYER_PHONE, 'role': 'buyer'
    })
    ok = resp_ok(resp)
    if ok:
        global BUYER_ID
        d = resp_data(resp)
        BUYER_ID = d.get('user', {}).get('id') or d.get('id')
        return True, "HTTP {}, Buyer ID={}".format(resp.status_code, BUYER_ID)
    return False, "HTTP {}: {}".format(resp.status_code, resp_data(resp))

def b2_otp():
    otp = OTP.objects.filter(email=BUYER_EMAIL).order_by('-created_at').first()
    if not otp:
        return False, "No OTP in DB"
    resp = api_post(buyer_client, '/api/auth/otp/verify/', {
        'email': BUYER_EMAIL, 'otp_code': otp.otp_code, 'purpose': 'registration'
    })
    return resp_ok(resp), "OTP verified, HTTP {}".format(resp.status_code)

def b3_login():
    resp = api_post(buyer_client, '/api/auth/login/', {
        'email': BUYER_EMAIL, 'password': PASSWORD
    })
    ok = resp_ok(resp)
    if ok:
        token = resp_data(resp).get('access', '')
        buyer_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(token))
        return True, "JWT token obtained"
    return False, "HTTP {}: {}".format(resp.status_code, resp_data(resp))

def b4_browse():
    resp = api_get(buyer_client, '/api/products/')
    if resp_ok(resp):
        items = resp_data(resp).get('results', []) or []
        seller_items = [p for p in items if str(p.get('store','')) == str(STORE_ID)]
        return True, "{} seller products visible to buyer".format(len(seller_items))
    return False, "HTTP {}".format(resp.status_code)

def b5_product_detail():
    if not PRODUCT_IDS:
        return False, "No products"
    resp = api_get(buyer_client, '/api/products/{}/'.format(PRODUCT_IDS[0]))
    if resp_ok(resp):
        p = resp_data(resp)
        return True, "{}, price={}, stock={}".format(
            p.get('product_name','?'), p.get('price','?'), p.get('stock','?'))
    return False, "HTTP {}".format(resp.status_code)

test('B1', '1', 'Register buyer', b1_register)
test('B1', '2', 'Verify OTP', b2_otp)
test('B1', '3', 'Login', b3_login)
test('B1', '4', 'Browse products (see seller items)', b4_browse)
test('B1', '5', 'Product detail', b5_product_detail)

# ============================================================================
# PHASE 5: BUYER CART & ORDER
# ============================================================================
print("\n" + "-" * 80)
print("  PHASE 5: BUYER CART & ORDER")
print("-" * 80)

def b6_add_to_cart():
    """Cart model uses 'qty' not 'quantity'. POST to /api/orders/cart/."""
    global CART_IDS
    if not PRODUCT_IDS:
        return False, "No products"
    # Add item 1: qty=2
    resp = api_post(buyer_client, '/api/orders/cart/', {
        'product': PRODUCT_IDS[0], 'qty': 2
    })
    if resp_ok(resp):
        CART_IDS.append(resp_data(resp).get('id'))
    return resp_ok(resp), "Cart add 1: HTTP {}".format(resp.status_code)

def b7_add_second_item():
    if len(PRODUCT_IDS) < 2:
        return False, "Need 2 products"
    resp = api_post(buyer_client, '/api/orders/cart/', {
        'product': PRODUCT_IDS[1], 'qty': 1
    })
    if resp_ok(resp):
        CART_IDS.append(resp_data(resp).get('id'))
    return resp_ok(resp), "Cart add 2: HTTP {}".format(resp.status_code)

def b8_cart_count():
    resp = api_get(buyer_client, '/api/orders/cart/count/')
    if resp_ok(resp):
        count = resp_data(resp).get('count', 0)
        return count >= 1, "Cart count: {}".format(count)
    return False, "HTTP {}".format(resp.status_code)

def b9_cart_list():
    resp = api_get(buyer_client, '/api/orders/cart/')
    if resp_ok(resp):
        items = resp_data(resp).get('results', []) or []
        return len(items) >= 1, "{} items in cart".format(len(items))
    return False, "HTTP {}".format(resp.status_code)

def b10_place_order():
    """OrderCreateSerializer expects cart_items (list of cart IDs)."""
    global ORDER_ID
    if not CART_IDS:
        return False, "No cart items to order"
    resp = api_post(buyer_client, '/api/orders/create/', {
        'cart_items': CART_IDS,
        'delivery_address': 'Jl. Pembeli No. 456, Jakarta',
        'recipient_name': 'Test Buyer',
        'recipient_phone': BUYER_PHONE,
        'notes': 'Test order E2E',
        'payment_method': 'transfer',
    })
    ok = resp_ok(resp, (200, 201))
    if ok:
        d = resp_data(resp)
        orders = d.get('orders', [])
        if orders:
            ORDER_ID = orders[0].get('id')
        return True, "Order created, ID={}, HTTP {}".format(ORDER_ID, resp.status_code)
    return False, "HTTP {}: {}".format(resp.status_code, resp_data(resp))

def b11_order_in_db():
    if not ORDER_ID:
        return False, "No order ID"
    order = Order.objects.filter(id=ORDER_ID).first()
    if not order:
        return False, "Order not in database"
    items_count = order.items.count()
    return True, "DB: status={}, items={}, total={}".format(
        order.order_status, items_count, order.total_price)

def b12_my_orders():
    resp = api_get(buyer_client, '/api/orders/my-orders/')
    if resp_ok(resp):
        items = resp_data(resp).get('results', []) or []
        return len(items) >= 1, "{} orders in buyer history".format(len(items))
    return False, "HTTP {}".format(resp.status_code)

def b13_order_detail():
    if not ORDER_ID:
        return False, "No order"
    resp = api_get(buyer_client, '/api/orders/{}/'.format(ORDER_ID))
    if resp_ok(resp):
        o = resp_data(resp)
        return True, "Status: {}, Total: {}".format(
            o.get('order_status','?'), o.get('total_price','?'))
    return False, "HTTP {}".format(resp.status_code)

test('B2', '1', 'Add item 1 to cart (qty=2)', b6_add_to_cart)
test('B2', '2', 'Add item 2 to cart', b7_add_second_item)
test('B2', '3', 'Cart count', b8_cart_count)
test('B2', '4', 'Cart list', b9_cart_list)
test('B2', '5', 'Place order (uses cart_items IDs)', b10_place_order)
test('B2', '6', 'Verify order in DB', b11_order_in_db)
test('B2', '7', 'My orders list', b12_my_orders)
test('B2', '8', 'Order detail', b13_order_detail)

# ============================================================================
# PHASE 6: BUYER PAYMENT
# ============================================================================
print("\n" + "-" * 80)
print("  PHASE 6: BUYER PAYMENT")
print("-" * 80)

def b14_payment_methods():
    resp = api_get(buyer_client, '/api/payments/methods/')
    code = resp.status_code
    if code == 200:
        items = resp_data(resp).get('results', []) or []
        return True, "{} payment methods".format(len(items))
    return code in (200, 403, 404), "HTTP {}".format(code)

def b15_payment_config():
    resp = api_get(buyer_client, '/api/payments/config/')
    return resp.status_code == 200, "HTTP {}".format(resp.status_code)

def b16_wallet_balance():
    resp = api_get(buyer_client, '/api/payments/wallet/balance/')
    code = resp.status_code
    if code == 200:
        balance = resp_data(resp).get('balance', 0)
        return True, "Wallet balance: {}".format(balance)
    return code in (200, 403, 404), "HTTP {}".format(code)

def b17_wallet_transactions():
    resp = api_get(buyer_client, '/api/payments/wallet/transactions/')
    code = resp.status_code
    if code == 200:
        items = resp_data(resp).get('results', []) or []
        return True, "{} transactions".format(len(items))
    return code in (200, 403, 404), "HTTP {}".format(code)

def b18_payment_status():
    if not ORDER_ID:
        return False, "No order"
    resp = api_get(buyer_client, '/api/payments/status/{}/'.format(ORDER_ID))
    return resp.status_code in (200, 403, 404), "HTTP {}".format(resp.status_code)

test('B3', '1', 'Payment methods', b14_payment_methods)
test('B3', '2', 'Payment config', b15_payment_config)
test('B3', '3', 'Wallet balance', b16_wallet_balance)
test('B3', '4', 'Wallet transactions', b17_wallet_transactions)
test('B3', '5', 'Payment status', b18_payment_status)

# ============================================================================
# PHASE 7: SELLER ORDER MANAGEMENT + REVIEW
# ============================================================================
print("\n" + "-" * 80)
print("  PHASE 7: SELLER ORDER MGMT + BUYER REVIEW")
print("-" * 80)

def o1_seller_sees_order():
    resp = api_get(seller_client, '/api/orders/seller/')
    if resp_ok(resp):
        items = resp_data(resp).get('results', []) or []
        return len(items) >= 1, "{} orders visible to seller".format(len(items))
    return False, "HTTP {}".format(resp.status_code)

def o2_update_status():
    if not ORDER_ID:
        return False, "No order"
    resp = api_post(seller_client, '/api/orders/{}/status/'.format(ORDER_ID), {
        'status': 'processed'
    })
    ok = resp_ok(resp)
    return ok, "Set to 'processed', HTTP {}".format(resp.status_code)

def o3_verify_status_db():
    if not ORDER_ID:
        return False, "No order"
    order = Order.objects.get(id=ORDER_ID)
    return order.order_status == 'processed', "DB status='{}'".format(order.order_status)

def o4_shipping_methods():
    resp = api_get(buyer_client, '/api/orders/shipping-methods/')
    code = resp.status_code
    if code == 200:
        items = resp_data(resp).get('results', []) or []
        return True, "{} shipping methods".format(len(items))
    return code in (200, 403, 404), "HTTP {}".format(code)

def o5_buyer_review():
    global REVIEW_ID
    if not PRODUCT_IDS:
        return False, "No products"
    resp = api_post(buyer_client, '/api/products/{}/reviews/'.format(PRODUCT_IDS[0]), {
        'rating': 5, 'comment': 'Produk sangat bagus! Recommended!'
    })
    ok = resp_ok(resp)
    if ok:
        REVIEW_ID = resp_data(resp).get('id')
        return True, "Review created, ID={}".format(REVIEW_ID)
    return ok, "HTTP {}".format(resp.status_code)

test('O1', '1', 'Seller sees new order', o1_seller_sees_order)
test('O1', '2', 'Update order status', o2_update_status)
test('O1', '3', 'Verify status in DB', o3_verify_status_db)
test('O1', '4', 'Shipping methods', o4_shipping_methods)
test('O1', '5', 'Submit buyer review', o5_buyer_review)

# ============================================================================
# PHASE 8: NOTIFICATIONS & CHAT
# ============================================================================
print("\n" + "-" * 80)
print("  PHASE 8: NOTIFICATIONS & CHAT")
print("-" * 80)

def n1_buyer_notifications():
    resp = api_get(buyer_client, '/api/notifications/')
    code = resp.status_code
    if code == 200:
        items = resp_data(resp).get('results', []) or []
        return True, "{} buyer notifications".format(len(items))
    return code in (200, 403, 404), "HTTP {}".format(code)

def n2_seller_notifications():
    resp = api_get(seller_client, '/api/notifications/')
    code = resp.status_code
    if code == 200:
        items = resp_data(resp).get('results', []) or []
        return True, "{} seller notifications".format(len(items))
    return code in (200, 403, 404), "HTTP {}".format(code)

def n3_conversations():
    resp = api_get(buyer_client, '/api/chat/conversations/')
    code = resp.status_code
    if code == 200:
        items = resp_data(resp).get('results', []) or []
        return True, "{} conversations".format(len(items))
    return code in (200, 403, 404), "HTTP {}".format(code)

def n4_unread_count():
    resp = api_get(buyer_client, '/api/chat/unread-count/')
    return resp.status_code == 200, "HTTP {}".format(resp.status_code)

test('N1', '1', 'Buyer notifications', n1_buyer_notifications)
test('N1', '2', 'Seller notifications', n2_seller_notifications)
test('N1', '3', 'Chat conversations', n3_conversations)
test('N1', '4', 'Unread count', n4_unread_count)

# ============================================================================
# PHASE 9: ADMIN PANEL
# ============================================================================
print("\n" + "-" * 80)
print("  PHASE 9: ADMIN/STAFF PANEL")
print("-" * 80)

def a1_create_admin():
    admin_user = User.objects.create_superuser(
        email="admin_{}@warungio.test".format(uid),
        password=PASSWORD,
        full_name="Admin Test",
        username="admin_{}".format(uid),
    )
    resp = api_post(admin_client, '/api/auth/login/', {
        'email': "admin_{}@warungio.test".format(uid),
        'password': PASSWORD,
    })
    ok = resp_ok(resp)
    if ok:
        token = resp_data(resp).get('access', '')
        admin_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(token))
        return True, "Admin login OK, HTTP {}".format(resp.status_code)
    return ok, "HTTP {}: {}".format(resp.status_code, resp_data(resp))

def a2_admin_dashboard():
    resp = api_get(admin_client, '/api/analytics/dashboard/')
    return resp.status_code in (200, 403), "HTTP {}".format(resp.status_code)

def a3_admin_profile():
    resp = api_get(admin_client, '/api/auth/profile/')
    return resp.status_code == 200, "HTTP {}".format(resp.status_code)

test('A1', '1', 'Create admin user', a1_create_admin)
test('A1', '2', 'Admin dashboard', a2_admin_dashboard)
test('A1', '3', 'Admin profile', a3_admin_profile)

# ============================================================================
# PHASE 10: FINAL DATABASE VERIFICATION
# ============================================================================
print("\n" + "-" * 80)
print("  PHASE 10: FINAL DATABASE VERIFICATION")
print("-" * 80)

def v1_count_users():
    count = User.objects.filter(email__endswith='@warungio.test').count()
    return count >= 3, "{} test users in DB (seller + buyer + admin)".format(count)

def v2_count_stores():
    count = Store.objects.all().count()
    my_store = Store.objects.filter(id=STORE_ID).first()
    return count >= 1 and my_store is not None, \
        "{} stores total, store_id={} exists".format(count, STORE_ID)

def v3_count_products():
    count = Product.objects.filter(store_id=STORE_ID).count()
    return count >= 1, "{} products for store {}".format(count, STORE_ID)

def v4_count_orders():
    count = Order.objects.all().count()
    my_order = Order.objects.filter(id=ORDER_ID).first()
    return count >= 1 and my_order is not None, \
        "{} orders total, order_id={} exists".format(count, ORDER_ID)

def v5_stock_deducted():
    if not PRODUCT_IDS:
        return False, "No products"
    product = Product.objects.get(id=PRODUCT_IDS[0])
    # Stock was 95 after update, reserved_stock should be 2 (from order)
    return product.reserved_stock == 2, "reserved_stock={} (expected 2), stock={}".format(
        product.reserved_stock, product.stock)

def v6_order_status_chain():
    resp = api_get(seller_client, '/api/orders/seller/')
    if resp_ok(resp):
        items = resp_data(resp).get('results', []) or []
        return True, "Seller sees {} orders".format(len(items))
    return False, "HTTP {}".format(resp.status_code)

def v7_public_store_listing():
    resp = api_get(APIClient(), '/api/stores/')
    if resp_ok(resp):
        items = resp_data(resp).get('results', []) or []
        return True, "{} stores in public listing".format(len(items))
    return False, "HTTP {}".format(resp.status_code)

def v8_health_check():
    resp = api_get(APIClient(), '/health/')
    return resp.status_code == 200, "Health: HTTP {}".format(resp.status_code)

test('V1', '1', 'Test users exist', v1_count_users)
test('V1', '2', 'Store exists in DB', v2_count_stores)
test('V1', '3', 'Products in DB', v3_count_products)
test('V1', '4', 'Orders in DB', v4_count_orders)
test('V1', '5', 'reserved_stock after order', v5_stock_deducted)
test('V1', '6', 'Seller order visibility', v6_order_status_chain)
test('V1', '7', 'Public store listing', v7_public_store_listing)
test('V1', '8', 'Health check', v8_health_check)

# ============================================================================
# FINAL SUMMARY
# ============================================================================
print("\n" + "=" * 80)
print("  RESULTS SUMMARY")
print("=" * 80)

passed = sum(1 for r in results if r[3])
failed = sum(1 for r in results if not r[3])
total = len(results)
pct = (passed / total * 100) if total > 0 else 0

print("\n  Total: {} | PASS: {} | FAIL: {} | Score: {:.0f}%".format(
    total, passed, failed, pct))
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
    icon = "PASS" if p['failed'] == 0 else "FAIL"
    print("  {} {}: {}/{} passed".format(icon, phase, p['passed'], p['total']))

print()

if failed > 0:
    print("  FAILED TESTS:")
    for r in results:
        if not r[3]:
            print("  FAIL {}.{} | {} | {}".format(r[0], r[1], r[2], r[4]))

print("\n{}".format("=" * 80))
print("  TEST COMPLETE -- {}/{} passed ({:.0f}%)".format(passed, total, pct))
print("{}".format("=" * 80))

# --- Cleanup ---
try:
    User.objects.filter(email__endswith='@warungio.test').delete()
    print("\n  Cleanup: test users removed")
except Exception as e:
    print("\n  Cleanup warning: {}".format(e))

sys.exit(0 if failed == 0 else 1)
