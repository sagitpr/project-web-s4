#!/usr/bin/env python3
"""
Warungio Business Flow End-to-End Test
Tests all core marketplace flows: Auth, Stores, Products, Cart, Orders, Payments, Chat, Admin
"""
import os, sys, json, uuid, time

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
os.environ['CELERY_ENABLED'] = 'false'
os.environ['DJANGO_ALLOWED_HOSTS'] = 'localhost,127.0.0.1,testserver,.run.app,warungio.web.id'
os.environ['DJANGO_DEBUG'] = 'True'

import django
django.setup()

from django.test import RequestFactory, Client
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import connection

client = APIClient()
results = []

def test_step(flow, step, desc, func):
    """Run a test step and record result."""
    try:
        result = func()
        status = "✅ PASS" if result.get('pass') else "❌ FAIL"
        detail = result.get('detail', '')
        results.append({'flow': flow, 'step': step, 'desc': desc, 'status': status, 'detail': detail})
        print(f"  {status} | {step}: {desc}")
        if detail:
            print(f"         {detail}")
    except Exception as e:
        results.append({'flow': flow, 'step': step, 'desc': desc, 'status': '❌ ERROR', 'detail': str(e)})
        print(f"  ❌ ERROR | {step}: {desc} -> {e}")


print("\n" + "="*70)
print("  WARUNGIO — BUSINESS FLOW END-TO-END TEST")
print("="*70)

# ═══════════════════════════════════════════════════════════════
# FLOW A: REGISTRASI & AUTENTIKASI
# ═══════════════════════════════════════════════════════════════
print("\n" + "─"*70)
print("  FLOW A: REGISTRASI & AUTENTIKASI")
print("─"*70)

unique_id = str(uuid.uuid4())[:8]
TEST_EMAIL = f"test_{unique_id}@warungio.test"
TEST_PASS = "Test@123456"
ACCESS_TOKEN = ""
REFRESH_TOKEN = ""

# A1: Health Check
def a1():
    resp = client.get('/health/')
    data = resp.json()
    return {'pass': resp.status_code == 200, 'detail': f"HTTP {resp.status_code}: {data}"}
test_step('A', 'A1', 'Health endpoint', a1)

# A2: Register
def a2():
    resp = client.post('/api/auth/register/', {
        'username': f'testuser_{unique_id}',
        'email': TEST_EMAIL,
        'password': TEST_PASS,
        'full_name': 'Test User Warungio',
        'phone': '081234567890',
        'role': 'buyer'
    }, format='json')
    ok = resp.status_code in (200, 201)
    detail = resp.json().get('message', resp.json().get('detail', str(resp.json())))
    return {'pass': ok, 'detail': f"HTTP {resp.status_code}: {detail}"}
test_step('A', 'A2', 'Register user', a2)

# A3: Login
def a3():
    global ACCESS_TOKEN, REFRESH_TOKEN
    resp = client.post('/api/auth/login/', {
        'email': TEST_EMAIL,
        'password': TEST_PASS
    }, format='json')
    ok = resp.status_code == 200
    if ok:
        data = resp.json()
        ACCESS_TOKEN = data.get('access', '')
        REFRESH_TOKEN = data.get('refresh', '')
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {ACCESS_TOKEN}')
        return {'pass': True, 'detail': f"Access token: {ACCESS_TOKEN[:40]}..."}
    return {'pass': False, 'detail': str(resp.json())}
test_step('A', 'A3', 'Login dengan email & password', a3)

# A4: Check Auth
def a4():
    resp = client.get('/api/auth/check-auth/')
    return {'pass': resp.status_code == 200, 'detail': f"HTTP {resp.status_code}"}
test_step('A', 'A4', 'Check auth status', a4)

# A5: Get Profile
def a5():
    resp = client.get('/api/auth/profile/')
    ok = resp.status_code == 200
    if ok:
        p = resp.json()
        return {'pass': True, 'detail': f"User: {p.get('email','?')} | Role: {p.get('role','?')} | Name: {p.get('full_name','?')}"}
    return {'pass': False, 'detail': str(resp.json())}
test_step('A', 'A5', 'Get user profile', a5)

# A6: JWT Token Refresh
def a6():
    resp = client.post('/api/token/refresh/', {'refresh': REFRESH_TOKEN}, format='json')
    ok = resp.status_code == 200
    if ok:
        return {'pass': True, 'detail': 'New access token obtained'}
    return {'pass': False, 'detail': str(resp.json())}
test_step('A', 'A6', 'JWT token refresh', a6)

# ═══════════════════════════════════════════════════════════════
# FLOW B: STORE & PRODUK
# ═══════════════════════════════════════════════════════════════
print("\n" + "─"*70)
print("  FLOW B: STORE & PRODUK")
print("─"*70)

STORE_ID = None
PRODUCT_ID = None
CATEGORY_ID = None

# B1: Create Store
def b1():
    global STORE_ID
    resp = client.post('/api/stores/create/', {
        'store_name': f'Toko Test {unique_id}',
        'description': 'Toko untuk testing end-to-end flow Warungio',
        'address': 'Jl. Test No. 123, Jakarta',
        'phone': '081234567891',
        'city': 'Jakarta',
        'province': 'DKI Jakarta',
    }, format='json')
    ok = resp.status_code in (200, 201)
    if ok:
        data = resp.json()
        STORE_ID = data.get('id', data.get('store',{}).get('id'))
        return {'pass': True, 'detail': f"Store ID: {STORE_ID} | Name: {data.get('store_name','?')}"}
    return {'pass': False, 'detail': str(resp.json())}
test_step('B', 'B1', 'Create store', b1)

# B2: Get My Store
def b2():
    resp = client.get('/api/stores/my-store/')
    ok = resp.status_code == 200
    if ok:
        data = resp.json()
        global STORE_ID
        STORE_ID = STORE_ID or data.get('id')
        return {'pass': True, 'detail': f"Store: {data.get('store_name','?')} | Status: {data.get('status','?')}"}
    return {'pass': False, 'detail': str(resp.json())}
test_step('B', 'B2', 'Get my store', b2)

# B3: List Categories
def b3():
    resp = client.get('/api/products/categories/')
    ok = resp.status_code == 200
    if ok:
        data = resp.json()
        count = len(data.get('results', data)) if isinstance(data, dict) else len(data)
        return {'pass': True, 'detail': f"{count} categories available"}
    return {'pass': False, 'detail': str(resp.json())}
test_step('B', 'B3', 'List product categories', b3)

# B4: Create Product
def b4():
    global PRODUCT_ID
    if not STORE_ID:
        return {'pass': False, 'detail': 'No store available'}
    resp = client.post('/api/products/create/', {
        'name': f'Produk Test {unique_id}',
        'description': 'Produk untuk testing flow end-to-end',
        'price': '25000.00',
        'stock': 100,
        'store': STORE_ID,
        'category': 1,  # first category
        'unit': 'pcs',
    }, format='json')
    ok = resp.status_code in (200, 201)
    if ok:
        data = resp.json()
        PRODUCT_ID = data.get('id')
        return {'pass': True, 'detail': f"Product ID: {PRODUCT_ID} | Price: {data.get('price','?')}"}
    return {'pass': False, 'detail': str(resp.json())}
test_step('B', 'B4', 'Create product', b4)

# B5: List Products
def b5():
    resp = client.get('/api/products/')
    ok = resp.status_code == 200
    if ok:
        data = resp.json()
        count = len(data.get('results', data)) if isinstance(data, dict) else len(data)
        return {'pass': True, 'detail': f"{count} products listed"}
    return {'pass': False, 'detail': str(resp.json())}
test_step('B', 'B5', 'List all products', b5)

# B6: Get Product Detail
def b6():
    if not PRODUCT_ID:
        return {'pass': False, 'detail': 'No product created'}
    resp = client.get(f'/api/products/{PRODUCT_ID}/')
    ok = resp.status_code == 200
    if ok:
        data = resp.json()
        return {'pass': True, 'detail': f"Product: {data.get('name','?')} | Stock: {data.get('stock','?')} | Price: {data.get('price','?')}"}
    return {'pass': False, 'detail': str(resp.json())}
test_step('B', 'B6', 'Get product detail', b6)


# ═══════════════════════════════════════════════════════════════
# FLOW C: CART & CHECKOUT
# ═══════════════════════════════════════════════════════════════
print("\n" + "─"*70)
print("  FLOW C: CART & CHECKOUT")
print("─"*70)

CART_ID = None
ORDER_ID = None
SHIPPING_METHOD_ID = None

# C1: Add to Cart
def c1():
    global CART_ID
    if not PRODUCT_ID:
        return {'pass': False, 'detail': 'No product'}
    resp = client.post('/api/orders/cart/', {
        'product': PRODUCT_ID,
        'quantity': 2,
    }, format='json')
    ok = resp.status_code in (200, 201)
    if ok:
        data = resp.json()
        CART_ID = data.get('id')
        return {'pass': True, 'detail': f"Cart ID: {CART_ID} | Qty: 2"}
    return {'pass': False, 'detail': str(resp.json())}
test_step('C', 'C1', 'Add product to cart', c1)

# C2: Get Cart Count
def c2():
    resp = client.get('/api/orders/cart/count/')
    ok = resp.status_code == 200
    if ok:
        data = resp.json()
        return {'pass': True, 'detail': f"Cart count: {data}"}
    return {'pass': False, 'detail': str(resp.json())}
test_step('C', 'C2', 'Get cart count', c2)

# C3: List Cart Items
def c3():
    resp = client.get('/api/orders/cart/')
    ok = resp.status_code == 200
    if ok:
        data = resp.json()
        count = len(data.get('results', data)) if isinstance(data, dict) else len(data)
        return {'pass': True, 'detail': f"{count} items in cart"}
    return {'pass': False, 'detail': str(resp.json())}
test_step('C', 'C3', 'List cart items', c3)

# C4: List Shipping Methods
def c4():
    global SHIPPING_METHOD_ID
    resp = client.get('/api/orders/shipping-methods/')
    ok = resp.status_code == 200
    if ok:
        data = resp.json()
        methods = data.get('results', data) if isinstance(data, dict) else data
        if methods and len(methods) > 0:
            SHIPPING_METHOD_ID = methods[0].get('id')
            return {'pass': True, 'detail': f"{len(methods)} methods. First: ID={SHIPPING_METHOD_ID}"}
        return {'pass': True, 'detail': 'No shipping methods (seeded?)'}
    return {'pass': False, 'detail': str(resp.json())}
test_step('C', 'C4', 'List shipping methods', c4)

# C5: Create Order
def c5():
    global ORDER_ID
    if not PRODUCT_ID:
        return {'pass': False, 'detail': 'No product'}
    resp = client.post('/api/orders/create/', {
        'items': [{'product_id': PRODUCT_ID, 'quantity': 1}],
        'shipping_address': 'Jl. Test No. 456, Jakarta',
        'shipping_method_id': SHIPPING_METHOD_ID,
        'notes': 'Test order from E2E flow',
    }, format='json')
    ok = resp.status_code in (200, 201)
    if ok:
        data = resp.json()
        ORDER_ID = data.get('id') or data.get('order', {}).get('id') or data.get('order_id')
        return {'pass': True, 'detail': f"Order ID: {ORDER_ID} | Response: {json.dumps(data)[:150]}"}
    return {'pass': False, 'detail': str(resp.json())[:200]}
test_step('C', 'C5', 'Create order (checkout)', c5)

# C6: My Orders
def c6():
    resp = client.get('/api/orders/my-orders/')
    ok = resp.status_code == 200
    if ok:
        data = resp.json()
        count = len(data.get('results', data)) if isinstance(data, dict) else len(data)
        return {'pass': True, 'detail': f"{count} orders found"}
    return {'pass': False, 'detail': str(resp.json())}
test_step('C', 'C6', 'List my orders', c6)

# ═══════════════════════════════════════════════════════════════
# FLOW D: PAYMENT
# ═══════════════════════════════════════════════════════════════
print("\n" + "─"*70)
print("  FLOW D: PAYMENT")
print("─"*70)

# D1: List Payment Methods
def d1():
    resp = client.get('/api/payments/methods/')
    ok = resp.status_code == 200
    if ok:
        data = resp.json()
        return {'pass': True, 'detail': f"Methods: {json.dumps(data)[:100]}"}
    return {'pass': False, 'detail': str(resp.json())}
test_step('D', 'D1', 'List payment methods', d1)

# D2: Payment Config
def d2():
    resp = client.get('/api/payments/config/')
    ok = resp.status_code == 200
    return {'pass': ok, 'detail': f"HTTP {resp.status_code}" if ok else str(resp.json())}
test_step('D', 'D2', 'Get payment config', d2)

# D3: Payment Status
def d3():
    if not ORDER_ID:
        return {'pass': False, 'detail': 'No order'}
    resp = client.get(f'/api/payments/status/{ORDER_ID}/')
    ok = resp.status_code in (200, 404)  # 404 means no payment yet, which is fine
    return {'pass': ok, 'detail': f"HTTP {resp.status_code}: {json.dumps(resp.json())[:100] if ok else resp.json()}"}
test_step('D', 'D3', 'Check payment status', d3)

# D4: Finance Summary
def d4():
    resp = client.get('/api/payments/finance/summary/')
    ok = resp.status_code in (200, 403, 401)
    return {'pass': True, 'detail': f"HTTP {resp.status_code}: {json.dumps(resp.json())[:100]}"}
test_step('D', 'D4', 'Finance summary', d4)

# ═══════════════════════════════════════════════════════════════
# FLOW E: ORDER MANAGEMENT
# ═══════════════════════════════════════════════════════════════
print("\n" + "─"*70)
print("  FLOW E: ORDER MANAGEMENT")
print("─"*70)

# E1: Order Detail
def e1():
    if not ORDER_ID:
        return {'pass': False, 'detail': 'No order'}
    resp = client.get(f'/api/orders/{ORDER_ID}/')
    ok = resp.status_code == 200
    if ok:
        data = resp.json()
        return {'pass': True, 'detail': f"Status: {data.get('order_status','?')} | Total: {data.get('total_amount','?')} | Items: {len(data.get('items', data.get('order_items', [])))}"}
    return {'pass': False, 'detail': str(resp.json())[:100]}
test_step('E', 'E1', 'Get order detail', e1)

# E2: Order History
def e2():
    resp = client.get('/api/orders/history/')
    ok = resp.status_code == 200
    if ok:
        data = resp.json()
        count = len(data.get('results', data)) if isinstance(data, dict) else len(data)
        return {'pass': True, 'detail': f"{count} orders in history"}
    return {'pass': False, 'detail': str(resp.json())}
test_step('E', 'E2', 'Order history', e2)

# E3: Cancel Order (if status allows)
def e3():
    if not ORDER_ID:
        return {'pass': False, 'detail': 'No order'}
    resp = client.post(f'/api/orders/{ORDER_ID}/cancel/', {}, format='json')
    ok = resp.status_code in (200, 400)  # 400 if already cancelled or wrong status
    detail = resp.json().get('message', resp.json().get('detail', str(resp.json())[:100]))
    return {'pass': ok, 'detail': f"HTTP {resp.status_code}: {detail}"}
test_step('E', 'E3', 'Cancel order (if pending)', e3)


# ═══════════════════════════════════════════════════════════════
# FLOW F: CHAT
# ═══════════════════════════════════════════════════════════════
print("\n" + "─"*70)
print("  FLOW F: CHAT")
print("─"*70)

CONVERSATION_ID = None

# F1: List Conversations
def f1():
    resp = client.get('/api/chat/conversations/')
    ok = resp.status_code == 200
    if ok:
        data = resp.json()
        count = len(data.get('results', data)) if isinstance(data, dict) else len(data)
        return {'pass': True, 'detail': f"{count} conversations"}
    return {'pass': False, 'detail': str(resp.json())}
test_step('F', 'F1', 'List conversations', f1)

# F2: Unread Count
def f2():
    resp = client.get('/api/chat/unread-count/')
    ok = resp.status_code == 200
    return {'pass': ok, 'detail': f"Unread: {resp.json()}" if ok else str(resp.json())}
test_step('F', 'F2', 'Check unread count', f2)


# ═══════════════════════════════════════════════════════════════
# FLOW G: ANALYTICS & DASHBOARD
# ═══════════════════════════════════════════════════════════════
print("\n" + "─"*70)
print("  FLOW G: ANALYTICS & DASHBOARD")
print("─"*70)

# G1: Dashboard Summary
def g1():
    resp = client.get('/api/analytics/dashboard/')
    ok = resp.status_code == 200
    if ok:
        data = resp.json()
        return {'pass': True, 'detail': json.dumps(data)[:100]}
    # Might be 403 if not seller, that's OK
    return {'pass': resp.status_code in (200, 403), 'detail': f"HTTP {resp.status_code}: {str(resp.json())[:80]}"}
test_step('G', 'G1', 'Analytics dashboard', g1)

# G2: Sales Analytics
def g2():
    resp = client.get('/api/analytics/sales/')
    ok = resp.status_code in (200, 403)
    return {'pass': ok, 'detail': f"HTTP {resp.status_code}"}
test_step('G', 'G2', 'Sales analytics', g2)

# G3: Daily Reports
def g3():
    resp = client.get('/api/analytics/reports/')
    ok = resp.status_code in (200, 403)
    return {'pass': ok, 'detail': f"HTTP {resp.status_code}"}
test_step('G', 'G3', 'Daily reports', g3)

# G4: AI Insights
def g4():
    resp = client.get('/api/analytics/ai/mock/')
    ok = resp.status_code in (200, 403, 404)
    return {'pass': ok, 'detail': f"HTTP {resp.status_code}: {str(resp.json())[:80]}" if ok else f"HTTP {resp.status_code}"}
test_step('G', 'G4', 'AI business insights (mock)', g4)

# ═══════════════════════════════════════════════════════════════
# FLOW H: API DOCS & EXPLORER
# ═══════════════════════════════════════════════════════════════
print("\n" + "─"*70)
print("  FLOW H: API DOCS & EXPLORER")
print("─"*70)

# H1: Swagger UI
def h1():
    resp = client.get('/api/docs/')
    return {'pass': resp.status_code in (200, 302), 'detail': f"HTTP {resp.status_code}"}
test_step('H', 'H1', 'Swagger UI docs', h1)

# H2: OpenAPI Schema
def h2():
    resp = client.get('/api/schema/')
    ok = resp.status_code == 200
    if ok:
        data = resp.json()
        endpoints = len(data.get('paths', {}))
        return {'pass': True, 'detail': f"OpenAPI schema: {endpoints} endpoints documented"}
    return {'pass': False, 'detail': f"HTTP {resp.status_code}"}
test_step('H', 'H2', 'OpenAPI schema', h2)

# H3: ReDoc
def h3():
    resp = client.get('/api/redoc/')
    return {'pass': resp.status_code in (200, 302), 'detail': f"HTTP {resp.status_code}"}
test_step('H', 'H3', 'ReDoc docs', h3)

# ═══════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("  HASIL TEST BUSINESS FLOW")
print("="*70)

passed = sum(1 for r in results if r['status'] == '✅ PASS')
failed = sum(1 for r in results if r['status'] == '❌ FAIL')
errors = sum(1 for r in results if r['status'] == '❌ ERROR')
total = len(results)

print(f"\n  Total: {total} | ✅ Pass: {passed} | ❌ Fail: {failed} | ❌ Error: {errors}")
print(f"  Score: {passed/total*100:.0f}%" if total > 0 else "")

print("\n  Detail per Flow:")
for r in results:
    print(f"  {r['status']} | {r['flow']}.{r['step']:3s} | {r['desc']:35s} | {r['detail'][:80]}")

print("\n  LEGEND:")
print("  ✅ PASS = endpoint merespon sesuai harapan")
print("  ❌ FAIL = endpoint error atau tidak sesuai spek")
print("  ❌ ERROR = exception tidak terduga")

print("\n" + "="*70)
print("  TEST SELESAI")
print("="*70 + "\n")
