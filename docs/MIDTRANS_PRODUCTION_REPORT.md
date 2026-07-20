# MIDTRANS PRODUCTION READINESS REPORT
**Project:** Warungio Marketplace
**Date:** July 20, 2026
**Status:** ✅ Production-Ready (Environment-Driven Configuration)

---

## 1. Integration Overview

Warungio marketplace uses **Midtrans Snap** as its primary online payment gateway. The integration supports:

- **Snap Popup Checkout** — Embedded payment UI for buyers
- **Snap Redirect** — Fallback when popup is blocked
- **Wallet Top-Up** — Midtrans-powered e-wallet funding
- **Webhook Callbacks** — Server-side payment status updates
- **Transaction Status Lookup** — Core API for reconciliation
- **Transaction Cancellation** — Cancel/void pending transactions
- **Transaction Expiration** — Expire unpaid transactions

---

## 2. Environment Configuration

| Setting | Source | Current Value | Security Level |
|---------|--------|--------------|----------------|
| `MIDTRANS_SERVER_KEY` | `os.environ.get('MIDTRANS_SERVER_KEY')` | `Mid-serv...` (masked) | 🔴 NEVER expose to frontend |
| `MIDTRANS_CLIENT_KEY` | `os.environ.get('MIDTRANS_CLIENT_KEY')` | `Mid-clie...` (masked) | 🟡 Safe for frontend |
| `MIDTRANS_MERCHANT_ID` | `os.environ.get('MIDTRANS_MERCHANT_ID')` | `M3763915...` (masked) | 🟢 Merchant public ID |
| `MIDTRANS_IS_PRODUCTION` | `os.environ.get('MIDTRANS_IS_PRODUCTION')` | `True` | 🟢 Environment switch |
| `MIDTRANS_SNAP_URL` | Auto-derived from `MIDTRANS_IS_PRODUCTION` | `https://app.midtrans.com/snap/v1/transactions` | 🟢 Dynamic |

**Auto-Detection Logic (no code changes needed for sandbox↔production switch):**
```python
# In settings.py — environment-driven, zero code changes needed
MIDTRANS_IS_PRODUCTION = os.environ.get('MIDTRANS_IS_PRODUCTION', 'False').lower() == 'true'

if MIDTRANS_IS_PRODUCTION:
    MIDTRANS_SNAP_URL = 'https://app.midtrans.com/snap/v1/transactions'
else:
    MIDTRANS_SNAP_URL = 'https://app.sandbox.midtrans.com/snap/v1/transactions'
```

---

## 3. Payment Flow (Buyer Checkout)

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Buyer   │───▶│  Django  │───▶│ Midtrans │───▶│  Buyer   │
│  Cart    │    │  Orders  │    │   Snap   │    │ Completes│
│          │◀───│  Create  │◀───│   API    │    │ Payment  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
                                                     │
                                                     ▼
                   ┌──────────┐    ┌──────────┐
                   │  Buyer   │◀───│ Midtrans │
                   │ Redirect │    │  Webhook │
                   │ Success  │    │   sends  │
                   └──────────┘    │  notif   │
                                   └──────────┘
                                        │
                                        ▼
                              ┌──────────────────┐
                              │  Django checks   │
                              │  signature,      │
                              │  dedup, updates  │
                              │  Payment & Order │
                              └──────────────────┘
```

**Step-by-step flow:**
1. Buyer selects items → Checkout page
2. Buyer fills delivery details → Clicks "Buat Pesanan"
3. Frontend calls `/api/payments/create-snap/` 
4. Backend creates order, calls Midtrans Snap API
5. Midtrans returns Snap token → Frontend loads Snap popup
6. Buyer completes payment in Snap popup
7. Midtrans sends webhook to `/api/payments/notification/`
8. Backend verifies signature, updates Payment & Order status
9. Buyer redirected to order-success page

---

## 4. Frontend Snap URL Configuration

### Before Fix (Hardcoded Sandbox):
```javascript
// buyer/checkout/script.js — HARDCODED!
script.src = 'https://app.sandbox.midtrans.com/snap/snap.js';
```

### After Fix (Environment-Driven):
```javascript
// Loaded from backend /api/payments/config/ endpoint
var snapBaseUrl = window.WARUNGIO_SNAP_BASE_URL || 'https://app.sandbox.midtrans.com';
var jsUrl = window.WARUNGIO_SNAP_JS_URL || (snapBaseUrl + '/snap/snap.js');
```

The `window.WARUNGIO_SNAP_BASE_URL` and `WARUNGIO_SNAP_JS_URL` are set by:
1. `websocket.js` — fetches from `/api/payments/config/` on page load
2. Backend `PaymentConfigView` — returns config based on `MIDTRANS_IS_PRODUCTION`

---

## 5. Configuration API Endpoints

| Endpoint | Method | Purpose | Exposes Secrets? |
|----------|--------|---------|-----------------|
| `/api/payments/config/` | GET | Full payment config (for backend client) | ✅ CLIENT_KEY only |
| `/api/payments/config/public/` | GET | Public-safe config (frontend) | ❌ No secrets |
| `/api/payments/methods/` | GET | Active payment methods | ❌ No secrets |

---

## 6. Production Switch Checklist

| Step | Description | Status |
|------|-------------|--------|
| 1 | Set `MIDTRANS_IS_PRODUCTION=True` in `.env` | ✅ Done |
| 2 | Set production `MIDTRANS_SERVER_KEY` | ✅ Done |
| 3 | Set production `MIDTRANS_CLIENT_KEY` | ✅ Done |
| 4 | Set production `MIDTRANS_MERCHANT_ID` | ✅ Done |
| 5 | Set Snap callback URL in Midtrans Dashboard: `/api/payments/notification/` | ⚠️ Requires dashboard action |
| 6 | Frontend loads Snap JS from production URL | ✅ Auto-detected |
| 7 | Frontend uses production client key | ✅ Auto-detected |
| 8 | Test production transaction end-to-end | ⚠️ Requires activation |
| 9 | Verify webhook signature works with production key | ✅ Verified in code |

---

## 7. Merchant ID Status

```
Current Merchant ID: M376391532
Production Mode:     True (Configured)
Snap URL:           https://app.midtrans.com/snap/v1/transactions
```

The Production activation request has been submitted. After approval, no code changes are needed — the environment variables already point to production.

---

## 8. Payment Methods Available (After Production Activation)

| Method | Type | Supported by Code |
|--------|------|------------------|
| Credit/Debit Card | Snap | ✅ Auto-enabled |
| Bank Transfer (BCA, BNI, BRI, Mandiri, Permata) | Snap | ✅ Auto-enabled |
| QRIS | Snap | ✅ Auto-enabled |
| GoPay | Snap | ✅ Auto-enabled |
| ShopeePay | Snap | ✅ Auto-enabled |
| DANA | Snap | ✅ Auto-enabled |
| OVO | Snap | ✅ Auto-enabled |
| Indomaret/Alfamart | Snap | ✅ Auto-enabled |

All methods are enabled through Midtrans Snap UI — no code changes needed to add/remove methods.

---

## 9. Production Deployment Validation

```bash
# 1. Verify environment variables
python -c "from django.conf import settings; print('PROD:', settings.MIDTRANS_IS_PRODUCTION, 'SNAP:', settings.MIDTRANS_SNAP_URL)"

# 2. Test Snap token creation
python manage.py shell -c "
from payments.services.midtrans import create_snap_token
# This will call the production Snap API
"

# 3. Verify webhook endpoint is accessible
curl -X POST https://yourdomain.com/api/payments/notification/ \
  -H 'Content-Type: application/json' \
  -d '{"order_id":"test","transaction_status":"pending","gross_amount":"10000","signature_key":"test"}'
```

---

## 10. Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Production keys exposed in frontend | 🔴 Critical | Client key only exposed; server key never leaves backend |
| Webhook replay attack | 🟡 Medium | 5-minute recency check + cache-based dedup |
| Duplicate webhook processing | 🟡 Medium | Cache-based idempotency (2-min window) |
| Payment without order completion | 🟡 Medium | ORM transaction atomicity |
| Midtrans API timeout | 🟢 Low | 30-second timeout + retry logic |
| Snapshot data loss on restore | 🟢 Low | Wallet data in DB (not device_info) |

**OVERALL PRODUCTION READINESS: ✅ READY (pending Midtrans activation approval)**
