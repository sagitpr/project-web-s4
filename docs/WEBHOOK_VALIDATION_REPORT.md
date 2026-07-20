# WEBHOOK VALIDATION REPORT
**Project:** Warungio Marketplace
**Date:** July 20, 2026
**Scope:** Midtrans webhook notification validation and processing

---

## 1. Webhook Endpoint

**URL:** `POST /api/payments/notification/`
**View:** `MidtransNotificationView`
**Authentication:** None (public — verified by signature)
**Rate Limit:** None configured

---

## 2. Webhook Processing Pipeline

```
Receive POST → Validate Serializer → Replay Check → Verify Signature
    → Dedup Check → Find Transaction → State Guard → Update Records
    → Status Handler → Response
```

### Stage 1: Serializer Validation
```python
serializer = MidtransNotificationSerializer(data=request.data)
serializer.is_valid(raise_exception=True)
```

Validated fields: `order_id`, `transaction_status`, `transaction_id`, `payment_type`, `gross_amount`, `fraud_status`, `signature_key`, `transaction_time`, `va_number`, `bank`, `status_code`, `status_message`

### Stage 2: Replay Attack Prevention ✅ (NEW)
5-minute recency check on `transaction_time`. Rejects notifications older than 300 seconds.

### Stage 3: Signature Verification ✅ (Upgraded)
SHA512 hash of `order_id + status_code + gross_amount + server_key`. Uses `hmac.compare_digest` for timing-attack-safe comparison.

### Stage 4: Idempotent Dedup ✅ (NEW)
Cache key `midtrans_dedup:{order_id}:{transaction_status}:{transaction_id}` with 120-second TTL. Prevents duplicate processing within 2 minutes.

### Stage 5: Transaction Lookup
Looks up `MidtransTransaction` by `order_id`. If not found, accepts as orphan for reconciliation.

### Stage 6: Monotonic State Machine ✅ (NEW)
Prevents late-arriving notifications from regressing confirmed states. If payment is `paid`/`refunded`/`chargeback`, incoming `deny`/`cancel`/`expire` are ignored.

### Stage 7: Status Handler
Maps Midtrans status → local status using comprehensive handler.

---

## 3. Status Mapping

| Midtrans Status | Local Status | Action |
|----------------|--------------|--------|
| `settlement` | `paid` | Mark order paid, create AdminFeeTxn, notify buyer+ seller |
| `capture` + `accept` | `paid` | Same as settlement |
| `capture` + `challenge` | `challenge` | Hold for review |
| `capture` + `deny` | `failed` | Mark failed |
| `pending` | `pending` | Already set (ignore) |
| `deny` | `failed` | Mark order cancelled |
| `cancel` | `cancelled` | Mark order cancelled |
| `expire` | `expired` | Mark order cancelled |
| `refund` | `refunded` | Mark refunded, notify buyer |
| `partial_refund` | `partial_refund` | Mark partial refund |
| `authorize` | `pending` | Ignore (pre-auth) |
| `chargeback` | `chargeback` | Mark chargeback, notify all |

---

## 4. Duplicate Notification Prevention

### Before Enhancement:
```python
if payment.payment_status in ('paid', 'refunded') and transaction_status in ('deny', 'cancel', 'expire'):
    # Only caught regressive transitions, not duplicate settlements
    return Response({'status': 'ignored', 'message': 'Already processed'})
```

### After Enhancement:
```python
# 1. Cache-based dedup (NEW)
dedup_key = f'midtrans_dedup:{order_id}:{transaction_status}:{transaction_id}'
if cache.get(dedup_key):
    return Response({'status': 'duplicate', 'message': 'Already processed'})
cache.set(dedup_key, True, 120)

# 2. Monotonic state guard (NEW)
if payment.payment_status in ('paid', 'refunded', 'chargeback'):
    if transaction_status in ('deny', 'cancel', 'expire', 'pending', 'authorize'):
        return Response({'status': 'ignored', 'message': 'State protected'})
```

---

## 5. Retry Logic

The webhook handler does NOT implement explicit retry logic. Midtrans will automatically retry failed webhooks (non-2xx responses) with exponential backoff up to 24 hours.

**Current response codes:**
| Response | Midtrans Action |
|----------|----------------|
| 200 OK | Stop retrying (success) |
| 400 Bad Request | Stop retrying (invalid payload) |
| 404 Not Found | Stop retrying (transaction unknown) |
| Any 5xx | Retry with backoff |

**Recommendation:** Add Celery task to periodically check pending Midtrans transactions that haven't received webhook callbacks (e.g., every 15 minutes, check transactions older than 30 minutes).

---

## 6. Orphan Webhook Handling ✅ (NEW)

```python
if not midtrans_tx:
    cache.set(f'midtrans_orphan:{order_id}', data, 3600)
    logger.warning('ORPHAN WEBHOOK: %s not found locally', order_id)
    return Response({'status': 'accepted_orphan', 'message': 'Logged for reconciliation'})
```

When a webhook arrives for an unknown order:
1. Returns 200 OK (stops Midtrans retries)
2. Caches payload for 1 hour
3. Logs warning for admin review
4. Admin can use `/admin/monitoring/reconciliation/` to manually link

---

## 7. Fraud & Challenge Handling ✅ (NEW)

```python
# Fraud challenge — payment held for review
if transaction_status == 'capture' and fraud_status == 'challenge':
    payment.payment_status = 'challenge'
    order.order_status = 'challenge'
    return Response({'status': 'challenge_accepted'})

# Chargeback — buyer disputed
if transaction_status == 'chargeback':
    payment.payment_status = 'chargeback'
    order.order_status = 'chargeback'
    notify_payment_update(status='chargeback')
    return Response({'status': 'chargeback_recorded'})
```

---

## 8. Webhook Testing

### Test Script
```python
# test_webhook.py — Simulate Midtrans webhook
import hashlib, hmac, json, requests

order_id = 'WRG-123-1234567890'
status_code = '200'
gross_amount = '50000'
server_key = 'Your Server Key Here'

payload = order_id + status_code + gross_amount + server_key
signature = hashlib.sha512(payload.encode()).hexdigest()

response = requests.post(
    'http://localhost:8000/api/payments/notification/',
    json={
        'order_id': order_id,
        'transaction_status': 'settlement',
        'transaction_id': 'trx-123',
        'payment_type': 'bank_transfer',
        'gross_amount': gross_amount,
        'fraud_status': 'accept',
        'status_code': status_code,
        'signature_key': signature,
        'transaction_time': '2026-07-20 10:00:00',
        'bank': 'bca',
        'va_number': '1234567890',
    }
)
print(f'Status: {response.status_code}, Body: {response.json()}')
```

---

## 9. Webhook Delivery Monitoring

**Current monitoring:**
- Logging at INFO/WARNING/ERROR levels for all webhook events
- Transaction status stored in `MidtransTransaction.transaction_status`
- Settlement time tracked in `MidtransTransaction.settlement_time`
- Raw response (masked) stored in `MidtransTransaction.raw_response`

**Recommended additions:**
- Add `WebhookDeliveryLog` model for delivery analytics
- Add admin dashboard for webhook delivery success rate
- Add alerting for webhook failures (e.g., signature verification failures > 5/hour)

---

## 10. Webhook Security Summary

| Security Feature | Status |
|-----------------|--------|
| Signature verification | ✅ SHA512 + hmac.compare_digest |
| Replay attack prevention | ✅ 5-min transaction_time window |
| Idempotent dedup | ✅ 2-min cache window |
| Monotonic state machine | ✅ Paid/refunded protected |
| Orphan webhook handling | ✅ Accepted + cached |
| Fraud challenge handling | ✅ Challenge → hold for review |
| Chargeback detection | ✅ Auto-status update |
| Sensitive data masking | ✅ Card data redacted |
| Rate limiting | ❌ Recommended |
| IP allowlist | ❌ Recommended |

**OVERALL WEBHOOK VALIDATION: ✅ PRODUCTION-GRADE**
