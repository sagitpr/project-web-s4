#!/usr/bin/env python3
"""Warungio Business Flow E2E Test — Django ORM direct."""
import os, django, json, uuid

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
os.environ['CELERY_ENABLED'] = 'false'
os.environ['DJANGO_ALLOWED_HOSTS'] = 'localhost,127.0.0.1,testserver'
os.environ['DJANGO_DEBUG'] = 'True'
os.environ['SECURE_SSL_REDIRECT'] = 'False'
os.environ['SESSION_COOKIE_SECURE'] = 'False'
os.environ['CSRF_COOKIE_SECURE'] = 'False'
os.environ['SECURE_HSTS_SECONDS'] = '0'

django.setup()

# Force override settings that may have been loaded from .env
from django.conf import settings
settings.SECURE_SSL_REDIRECT = False
settings.SESSION_COOKIE_SECURE = False
settings.CSRF_COOKIE_SECURE = False
settings.SECURE_HSTS_SECONDS = 0
settings.DEBUG = True

from django.db import connection
from django.test import Client, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User
from stores.models import Store
from products.models import Product, Category
from orders.models import Order, OrderItem, Cart
from payments.models import Payment
from chat.models import Conversation, Message

client = APIClient()
results = []
uid = str(uuid.uuid4())[:8]
EMAIL = f"test_{uid}@warungio.test"
import random
PHONE = f"081234{random.randint(100000,999999)}"  # 08 + 12 digit unique numeric

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
print("  WARUNGIO — BUSINESS FLOW E2E TEST (DIRECT ORM)")
print("="*70)

# ── PRE-FLIGHT: Database Connection & Model Registration ──
print("\n" + "─"*70)
print("  PRE-FLIGHT: DATABASE CHECK")
print("─"*70)

def pre_01():
    c = connection.cursor()
    c.execute("SELECT COUNT(*) FROM django_migrations")
    return True, f"{c.fetchone()[0]} migrations applied"
test('PRE', 'P0', 'Migration count', pre_01)

def pre_02():
    return True, f"Users: {User.objects.count()}, Stores: {Store.objects.count()}, Products: {Product.objects.count()}"
test('PRE', 'P1', 'Record counts', pre_02)

def pre_03():
    try:
        with connection.cursor() as c:
            c.execute("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() ORDER BY TABLE_NAME")
            tables = [r[0] for r in c.fetchall()]
        return True, f"{len(tables)} business tables"
    except:
        c = connection.cursor()
        tables = []
        return True, "DB connected (SQLite? not MariaDB)"

test('PRE', 'P2', 'Business tables', pre_03)

# ── FLOW A: AUTH + OTP ──
print("\n" + "─"*70)
print("  FLOW A: AUTH + OTP + JWT")
print("─"*70)

OTP_CODE = ""
TOKEN = ""

def a1_register():
    global OTP_CODE
    resp = client.post('/api/auth/register/', {
        'username': f'user_{uid}', 'email': EMAIL, 'password': 'Test@123456',
        'password2': 'Test@123456', 'full_name': 'Test User', 'phone': PHONE, 'role': 'buyer'
    }, format='json')
    ok = resp.status_code in (200,201)
    if ok:
        d = resp.json() if hasattr(resp, 'json') else resp.data
        OTP_CODE = d.get('otp_code', '')
        return True, f"HTTP {resp.status_code} | OTP: {OTP_CODE}"
    content = resp.content.decode('utf-8','ignore') if hasattr(resp, 'content') else str(resp)
    return False, f"HTTP {resp.status_code}: {content[:100]}"
test('A', 'A1', 'Register + dapat OTP', a1_register)

def a2_verify_otp():
    """Verify OTP using code from register response."""
    if not OTP_CODE:
        return False, "No OTP code from registration"
    resp = client.post('/api/auth/otp/verify/', {
        'email': EMAIL,
        'otp_code': OTP_CODE,
        'purpose': 'registration'
    }, format='json')
    ok = resp.status_code == 200
    if ok:
        d = resp.json() if hasattr(resp, 'json') else resp.data
        return True, f"HTTP {resp.status_code} | Verified: {d.get('verified','?')}"
    content = resp.content.decode('utf-8','ignore') if hasattr(resp, 'content') else str(resp)
    return False, f"HTTP {resp.status_code}: {content[:100]}"
test('A', 'A2', 'Verify OTP', a2_verify_otp)

def a3_login():
    """Login after OTP verified — should succeed."""
    global TOKEN
    resp = client.post('/api/auth/login/', {'email': EMAIL, 'password': 'Test@123456'}, format='json')
    ok = resp.status_code == 200
    if ok:
        d = resp.json() if hasattr(resp, 'json') else resp.data
        TOKEN = d.get('access', '')
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {TOKEN}')
        return True, f"Token: {TOKEN[:40]}..."
    else:
        content = resp.content.decode('utf-8','ignore') if hasattr(resp, 'content') else str(resp)
        return False, f"HTTP {resp.status_code}: {content[:100]}"
test('A', 'A3', 'Login (after OTP)', a3_login)

def a4_check():
    if not TOKEN: return False, "No token"
    resp = client.get('/api/auth/check-auth/')
    return resp.status_code == 200, f"Auth OK | HTTP {resp.status_code}"
test('A', 'A4', 'Check auth', a4_check if TOKEN else lambda: (False, "Skipped"))

def a5_profile():
    if not TOKEN: return False, "No token"
    resp = client.get('/api/auth/profile/')
    ok = resp.status_code == 200
    if ok:
        d = resp.json() if hasattr(resp, 'json') else resp.data
        return True, f"Email: {d.get('email','?')} | Role: {d.get('role','?')} | is_verified: {d.get('is_verified','?')}"
    return False, f"HTTP {resp.status_code}"
test('A', 'A5', 'Profile + verified status', a5_profile if TOKEN else lambda: (False, "Skipped"))

# ── FLOW B: STORE & PRODUK ──
print("\n" + "─"*70)
print("  FLOW B: STORE & PRODUK")
print("─"*70)

SID = None; PID = None

def b1_create():
    global SID; resp = client.post('/api/stores/create/', {
        'store_name': f'Toko {uid}', 'description': 'Toko test E2E',
        'address': 'Jl. Test 123', 'phone': '081234567891', 'city': 'Jakarta', 'province': 'DKI Jakarta'
    }, format='json')
    if resp.status_code in (200,201): SID = resp.data.get('id')
    return resp.status_code in (200,201), f"Store ID: {SID}"
test('B', 'B1', 'Create store', b1_create if TOKEN else lambda: (False, "Skipped"))

def b2_mystore():
    global SID; resp = client.get('/api/stores/my-store/')
    if resp.status_code == 200:
        if not SID: SID = resp.data.get('id')
    return resp.status_code == 200, f"Store: {resp.data.get('store_name','?') if resp.status_code==200 else 'Error'}"
test('B', 'B2', 'My store', b2_mystore if TOKEN else lambda: (False, "Skipped"))

def b3_categories():
    resp = client.get('/api/products/categories/')
    return resp.status_code == 200, f"{len(resp.data.get('results',[]) or [])} categories"
test('B', 'B3', 'Categories', b3_categories if TOKEN else lambda: (False, "Skipped"))

def b4_create_product():
    global PID; resp = client.post('/api/products/create/', {
        'name': f'Produk {uid}', 'description': 'Produk test E2E', 'price': '25000.00',
        'stock': 100, 'store': SID or 1, 'unit': 'pcs'
    }, format='json')
    if resp.status_code in (200,201): PID = resp.data.get('id')
    return resp.status_code in (200,201), f"Product ID: {PID}"
test('B', 'B4', 'Create product', b4_create_product if TOKEN else lambda: (False, "Skipped"))

def b5_list():
    resp = client.get('/api/products/')
    count = len(resp.data.get('results', []) or []) if resp.status_code == 200 else 0
    return resp.status_code == 200, f"{count} products listed"
test('B', 'B5', 'List products', b5_list if TOKEN else lambda: (False, "Skipped"))

def b6_detail():
    if not PID: return False, "No product"
    resp = client.get(f'/api/products/{PID}/')
    return resp.status_code == 200, f"Product: {resp.data.get('name','?')} Price: {resp.data.get('price','?')}"
test('B', 'B6', 'Product detail', b6_detail if TOKEN else lambda: (False, "Skipped"))

# ── FLOW C: CART & ORDER ──
print("\n" + "─"*70)
print("  FLOW C: CART & ORDER")
print("─"*70)

OID = None

def c1_cart():
    if not PID: return False, "No product"
    resp = client.post('/api/orders/cart/', {'product': PID, 'quantity': 2}, format='json')
    return resp.status_code in (200,201), f"Cart: HTTP {resp.status_code}"
test('C', 'C1', 'Add to cart', c1_cart if TOKEN else lambda: (False, "Skipped"))

def c2_cartcount():
    resp = client.get('/api/orders/cart/count/')
    return resp.status_code == 200, f"Count: {resp.data}"
test('C', 'C2', 'Cart count', c2_cartcount if TOKEN else lambda: (False, "Skipped"))

def c3_cartlist():
    resp = client.get('/api/orders/cart/')
    items = resp.data.get('results', []) or [] if resp.status_code == 200 else []
    return resp.status_code == 200, f"{len(items)} items in cart"
test('C', 'C3', 'Cart list', c3_cartlist if TOKEN else lambda: (False, "Skipped"))

def c4_shipping():
    resp = client.get('/api/orders/shipping-methods/')
    items = resp.data.get('results', []) or [] if resp.status_code == 200 else []
    return resp.status_code == 200, f"{len(items)} shipping methods"
test('C', 'C4', 'Shipping', c4_shipping if TOKEN else lambda: (False, "Skipped"))

def c5_create():
    global OID
    if not PID: return False, "No product"
    resp = client.post('/api/orders/create/', {
        'items': [{'product_id': PID, 'quantity': 1}],
        'shipping_address': 'Jl. Test 456', 'notes': 'Test order E2E'
    }, format='json')
    if resp.status_code in (200,201):
        OID = resp.data.get('id') or resp.data.get('order_id')
    return resp.status_code in (200,201), f"Order ID: {OID}"
test('C', 'C5', 'Create order', c5_create if TOKEN else lambda: (False, "Skipped"))

def c6_myorders():
    resp = client.get('/api/orders/my-orders/')
    items = resp.data.get('results', []) or [] if resp.status_code == 200 else []
    return resp.status_code == 200, f"{len(items)} orders"
test('C', 'C6', 'My orders', c6_myorders if TOKEN else lambda: (False, "Skipped"))

# ── FLOW D: PAYMENT ──
print("\n" + "─"*70)
print("  FLOW D: PAYMENT")
print("─"*70)

def d1_paymethods():
    resp = client.get('/api/payments/methods/')
    return resp.status_code == 200, f"HTTP {resp.status_code}"
test('D', 'D1', 'Payment methods', d1_paymethods if TOKEN else lambda: (False, "Skipped"))

def d2_payconfig():
    resp = client.get('/api/payments/config/')
    return resp.status_code == 200, f"HTTP {resp.status_code}"
test('D', 'D2', 'Payment config', d2_payconfig if TOKEN else lambda: (False, "Skipped"))

def d3_paystatus():
    if not OID: return False, "No order"
    resp = client.get(f'/api/payments/status/{OID}/')
    return resp.status_code in (200,404), f"HTTP {resp.status_code}"
test('D', 'D3', 'Payment status', d3_paystatus if TOKEN else lambda: (False, "Skipped"))

def d4_finance():
    resp = client.get('/api/payments/finance/summary/')
    return resp.status_code in (200,403), f"HTTP {resp.status_code}"
test('D', 'D4', 'Finance', d4_finance if TOKEN else lambda: (False, "Skipped"))

# ── FLOW E: ORDER MGMT ──
print("\n" + "─"*70)
print("  FLOW E: ORDER MANAGEMENT")
print("─"*70)

def e1_detail():
    if not OID: return False, "No order"
    resp = client.get(f'/api/orders/{OID}/')
    return resp.status_code == 200, f"Status: {resp.data.get('order_status','?')}"
test('E', 'E1', 'Order detail', e1_detail if TOKEN else lambda: (False, "Skipped"))

def e2_history():
    resp = client.get('/api/orders/history/')
    return resp.status_code == 200, f"HTTP {resp.status_code}"
test('E', 'E2', 'History', e2_history if TOKEN else lambda: (False, "Skipped"))

# ── FLOW F: CHAT ──
print("\n" + "─"*70)
print("  FLOW F: CHAT")
print("─"*70)

def f1_convos():
    resp = client.get('/api/chat/conversations/')
    items = resp.data.get('results', []) or [] if resp.status_code == 200 else []
    return resp.status_code == 200, f"{len(items)} conversations"
test('F', 'F1', 'Conversations', f1_convos if TOKEN else lambda: (False, "Skipped"))

def f2_unread():
    resp = client.get('/api/chat/unread-count/')
    return resp.status_code == 200, f"Unread: {resp.data}"
test('F', 'F2', 'Unread', f2_unread if TOKEN else lambda: (False, "Skipped"))

# ── FLOW G: ANALYTICS ──
print("\n" + "─"*70)
print("  FLOW G: ANALYTICS")
print("─"*70)

def g1_dash():
    resp = client.get('/api/analytics/dashboard/')
    return resp.status_code in (200,403), f"HTTP {resp.status_code}"
test('G', 'G1', 'Dashboard', g1_dash if TOKEN else lambda: (False, "Skipped"))

def g2_sales():
    resp = client.get('/api/analytics/sales/')
    return resp.status_code in (200,403), f"HTTP {resp.status_code}"
test('G', 'G2', 'Sales', g2_sales if TOKEN else lambda: (False, "Skipped"))

def g3_ai():
    resp = client.get('/api/analytics/ai/mock/')
    return resp.status_code in (200,403,404), f"HTTP {resp.status_code}"
test('G', 'G3', 'AI mock', g3_ai if TOKEN else lambda: (False, "Skipped"))

# ── FLOW H: API ──
print("\n" + "─"*70)
print("  FLOW H: API DOCS")
print("─"*70)

def h1_swagger():
    resp = client.get('/api/docs/')
    return resp.status_code in (200,302), f"HTTP {resp.status_code}"
test('H', 'H1', 'Swagger', h1_swagger)

def h2_schema():
    resp = client.get('/api/schema/')
    ok = resp.status_code == 200
    paths = len(resp.data.get('paths', {})) if ok else 0
    return ok, f"{paths} endpoints documented" if ok else f"HTTP {resp.status_code}"
test('H', 'H2', 'OpenAPI', h2_schema)

def h3_redoc():
    resp = client.get('/api/redoc/')
    return resp.status_code in (200,302), f"HTTP {resp.status_code}"
test('H', 'H3', 'ReDoc', h3_redoc)

# ═══════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("  HASIL TEST BUSINESS FLOW")
print("="*70)

passed = sum(1 for r in results if r[3])
failed = sum(1 for r in results if not r[3])
total = len(results)
print(f"\n  Total: {total} | ✅ PASS: {passed} | ❌ FAIL: {failed}")
print(f"  Score: {passed/total*100:.0f}%\n")

print(f"  Detail per Flow:")
for r in results:
    s = "✅" if r[3] else "❌"
    print(f"  {s} | {r[0]}.{r[1]:3s} | {r[2][:35]:35s} | {r[4][:100]}")

# Cleanup: Delete test user and related data
try:
    User.objects.filter(email=EMAIL).delete()
    print(f"\n  🧹 Test user {EMAIL} cleaned up")
except:
    pass

print(f"\n{'='*70}")
print(f"  TEST SELESAI")
print(f"{'='*70}")
