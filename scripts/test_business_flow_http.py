#!/usr/bin/env python3
"""
Warungio Business Flow E2E Test — REAL HTTP via requests library
All URLs via localhost:8000 with verify=False
"""
import json, uuid, requests

BASE = "http://localhost:8000"

def api(method, path, data=None, token=None):
    url = BASE + path
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    try:
        resp = requests.request(method, url, json=data, headers=headers, 
                               timeout=10, allow_redirects=True, verify=False)
        is_json = 'application/json' in resp.headers.get('Content-Type', '')
        body = resp.json() if is_json and resp.text else resp.text[:200]
        return {'status': resp.status_code, 'ok': is_json and resp.ok, 'data': body, 'json': is_json}
    except Exception as e:
        return {'status': 0, 'ok': False, 'data': str(e)[:150], 'json': False}

results = []
uid = str(uuid.uuid4())[:8]
EMAIL = f"test_{uid}@warungio.test"
PASS = "Test@123456"
TOKEN = ""

def log(f, s, d, r):
    ok = "✅" if r['ok'] else "❌"
    dt = json.dumps(r['data']) if isinstance(r['data'], (dict,list)) else str(r['data'])[:120]
    results.append({'flow': f, 'step': s, 'desc': d, 'pass': r['ok'], 'status': r['status'], 'detail': dt})
    print(f"  {ok} | {s}: {d} -> HTTP {r['status']} | {dt}")

print(f"\n{'='*70}")
print(f"  WARUNGIO — BUSINESS FLOW E2E TEST (REAL HTTP)")
print(f"{'='*70}")

# ── FLOW A: HEALTH & AUTH ──
print(f"\n{'─'*70}")
print(f"  FLOW A: HEALTH & AUTENTIKASI")
print(f"{'─'*70}")

log('A','A1','Health', api('GET','/health/'))
log('A','A2','Register', api('POST','/api/auth/register/',{'username':f'user_{uid}','email':EMAIL,'password':PASS,'full_name':'Test User','phone':'081234567890','role':'buyer'}))
log('A','A3','Login', api('POST','/api/auth/login/',{'email':EMAIL,'password':PASS}))
# Extract token
r = api('POST','/api/auth/login/',{'email':EMAIL,'password':PASS})
if r['ok'] and isinstance(r['data'], dict):
    TOKEN = r['data'].get('access','')
    print(f"         TOKEN: {TOKEN[:50]}...")

if TOKEN:
    log('A','A4','Check auth', api('GET','/api/auth/check-auth/', token=TOKEN))
    log('A','A5','Profile', api('GET','/api/auth/profile/', token=TOKEN))

# ── FLOW B: STORE & PRODUK ──
print(f"\n{'─'*70}")
print(f"  FLOW B: STORE & PRODUK")
print(f"{'─'*70}")

SID = None; PID = None

if TOKEN:
    log('B','B1','Create store', api('POST','/api/stores/create/',{'store_name':f'Toko {uid}','description':'Toko test','address':'Jl. Test 123','phone':'081234567891','city':'Jakarta','province':'DKI Jakarta'}, token=TOKEN))
    r = api('POST','/api/stores/create/',{'store_name':f'Toko {uid}','description':'Toko test','address':'Jl. Test 123','phone':'081234567891','city':'Jakarta','province':'DKI Jakarta'}, token=TOKEN)
    if r['ok'] and isinstance(r['data'], dict):
        SID = r['data'].get('id') or r['data'].get('store',{}).get('id')
    
    log('B','B2','My store', api('GET','/api/stores/my-store/', token=TOKEN))
    r2 = api('GET','/api/stores/my-store/', token=TOKEN)
    if r2['ok'] and isinstance(r2['data'], dict):
        SID = SID or r2['data'].get('id')
    
    log('B','B3','Categories', api('GET','/api/products/categories/', token=TOKEN))
    
    log('B','B4','Create product', api('POST','/api/products/create/',{'name':f'Produk {uid}','description':'Produk test','price':'25000.00','stock':100,'store':SID or 1,'unit':'pcs'}, token=TOKEN))
    r3 = api('POST','/api/products/create/',{'name':f'Produk {uid}','description':'Produk test','price':'25000.00','stock':100,'store':SID or 1,'unit':'pcs'}, token=TOKEN)
    if r3['ok'] and isinstance(r3['data'], dict):
        PID = r3['data'].get('id')
    
    log('B','B5','List products', api('GET','/api/products/', token=TOKEN))
    if PID:
        log('B','B6','Product detail', api('GET',f'/api/products/{PID}/', token=TOKEN))

# ── FLOW C: CART & ORDER ──
print(f"\n{'─'*70}")
print(f"  FLOW C: CART & ORDER")
print(f"{'─'*70}")

OID = None
if TOKEN and PID:
    log('C','C1','Add to cart', api('POST','/api/orders/cart/',{'product':PID,'quantity':2}, token=TOKEN))
    log('C','C2','Cart count', api('GET','/api/orders/cart/count/', token=TOKEN))
    log('C','C3','Cart list', api('GET','/api/orders/cart/', token=TOKEN))
    log('C','C4','Shipping', api('GET','/api/orders/shipping-methods/', token=TOKEN))
    log('C','C5','Create order', api('POST','/api/orders/create/',{'items':[{'product_id':PID,'quantity':1}],'shipping_address':'Jl.Test 456','notes':'Test'}, token=TOKEN))
    r4 = api('POST','/api/orders/create/',{'items':[{'product_id':PID,'quantity':1}],'shipping_address':'Jl.Test 456','notes':'Test'}, token=TOKEN)
    if r4['ok'] and isinstance(r4['data'], dict):
        OID = r4['data'].get('id') or r4['data'].get('order_id')
    log('C','C6','My orders', api('GET','/api/orders/my-orders/', token=TOKEN))

# ── FLOW D: PAYMENT ──
print(f"\n{'─'*70}")
print(f"  FLOW D: PAYMENT")
print(f"{'─'*70}")
if TOKEN:
    log('D','D1','Methods', api('GET','/api/payments/methods/', token=TOKEN))
    log('D','D2','Config', api('GET','/api/payments/config/', token=TOKEN))
    log('D','D4','Finance', api('GET','/api/payments/finance/summary/', token=TOKEN))
    if OID: log('D','D3','Status', api('GET',f'/api/payments/status/{OID}/', token=TOKEN))

# ── FLOW E: ORDER MGMT ──
print(f"\n{'─'*70}")
print(f"  FLOW E: ORDER MANAGEMENT")
print(f"{'─'*70}")
if TOKEN:
    log('E','E2','History', api('GET','/api/orders/history/', token=TOKEN))
    if OID:
        log('E','E1','Detail', api('GET',f'/api/orders/{OID}/', token=TOKEN))
        log('E','E3','Cancel', api('POST',f'/api/orders/{OID}/cancel/',{}, token=TOKEN))

# ── FLOW F: CHAT ──
print(f"\n{'─'*70}")
print(f"  FLOW F: CHAT")
print(f"{'─'*70}")
if TOKEN:
    log('F','F1','Conversations', api('GET','/api/chat/conversations/', token=TOKEN))
    log('F','F2','Unread', api('GET','/api/chat/unread-count/', token=TOKEN))

# ── FLOW G: ANALYTICS ──
print(f"\n{'─'*70}")
print(f"  FLOW G: ANALYTICS")
print(f"{'─'*70}")
if TOKEN:
    log('G','G1','Dashboard', api('GET','/api/analytics/dashboard/', token=TOKEN))
    log('G','G2','Sales', api('GET','/api/analytics/sales/', token=TOKEN))
    log('G','G3','AI Mock', api('GET','/api/analytics/ai/mock/', token=TOKEN))

# ── FLOW H: API DOCS ──
print(f"\n{'─'*70}")
print(f"  FLOW H: API DOCS")
print(f"{'─'*70}")
log('H','H1','Swagger', api('GET','/api/docs/'))
log('H','H2','OpenAPI', api('GET','/api/schema/'))

# ── SUMMARY ──
print(f"\n{'='*70}")
print(f"  HASIL TEST BUSINESS FLOW")
print(f"{'='*70}")

passed = sum(1 for r in results if r['pass'])
failed = sum(1 for r in results if not r['pass'])
total = len(results)
print(f"\n  Total: {total} | ✅ PASS: {passed} | ❌ FAIL: {failed} | Score: {passed/total*100:.0f}%\n")

print(f"  Detail:")
for r in results:
    s = "✅" if r['pass'] else "❌"
    print(f"  {s} | {r['flow']}.{r['step']:3s} | {r['desc'][:35]:35s} | HTTP {r['status']:3d} | {r['detail'][:100]}")
print(f"\n{'='*70}")
print(f"  TEST SELESAI")
print(f"{'='*70}")
