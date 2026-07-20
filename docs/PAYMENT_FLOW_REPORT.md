# PAYMENT FLOW REPORT
**Project:** Warungio Marketplace
**Date:** July 20, 2026
**Scope:** Complete payment flow analysis — Buyer, Seller, Admin, Wallet, Refund

---

## 1. Buyer Checkout Flow

### 1.1 Frontend Flow
```
Cart Page → Checkout Page → Order Created → Midtrans Snap Popup → Order Success
                                                                         │
                                                                    [Payment Polling]
```

### 1.2 API Call Sequence
```
1. GET /api/payments/methods/           → Load payment method options
2. GET /api/payments/config/            → Get client key + snap URL
3. POST /orders/create/                 → Create order(s)
4. POST /api/payments/create-snap/      → Create Snap token
5. Midtrans Snap popup (client-side)    → Buyer completes payment
6. GET /api/payments/status/{order_id}/ → Poll payment status
```

### 1.3 Database State Changes
```
Order: pending → paid (via webhook)
Payment: pending → paid (via webhook)
MidtransTransaction: pending → settlement (via webhook)
Wallet: balance += amount (for top-up orders)
```

---

## 2. Seller Payment Flow

### 2.1 Bank Account Setup
```
Seller Dashboard → Finance → Bank Accounts → Add Bank Account
                                                │
                                                ▼
                                    POST /api/payments/finance/bank-accounts/
                                    Save: bank_name, account_number, account_holder
                                    Auto-set primary if first account
```

### 2.2 Withdrawal Flow
```
Seller Dashboard → Finance → Withdraw
                        │
                        ▼
   1. POST /api/payments/finance/withdraw/
   2. Validate: amount > 10,000, amount < 1,000,000,000
   3. Validate: primary bank account exists
   4. Validate: available_balance >= amount
   5. Create Payment(type='withdrawal', status='pending')
   6. Debit wallet atomically via WalletService
   7. Send notification
```

### 2.3 Finance Summary
```python
total_income_net = completed_orders_total - total_admin_fees
available_balance = total_income_net - total_withdrawals_paid_and_pending
```

---

## 3. Wallet Top-Up Flow

```
Buyer Dashboard → Wallet → Top Up
                        │
                        ▼
   1. POST /api/payments/wallet/topup/
   2. Validate: amount >= 10,000
   3. Create virtual Order(notes='TOPUP')
   4. Create Snap token via Midtrans
   5. Open Snap popup
   6. On success (webhook): credit_wallet()
```

**Webhook detection for top-up:**
```python
is_topup = (order and order.notes == 'TOPUP') or (order_id and 'TOP-' in order_id)
if is_topup:
    credit_wallet(user=user, amount=gross_amount, tx_type='topup')
```

---

## 4. Refund Flow

### 4.1 Refund Request
```
Buyer submits refund → Refund status: pending
                             │
                             ▼
              Seller responds: approve/reject
                             │
                             ▼
         If approved: Payment status → refunded
                      Order status → refunded
                      Wallet: credit_wallet(tx_type='refund')
```

### 4.2 Refund Webhook Handling
```python
if transaction_status == 'refund':
    payment.payment_status = 'refunded'
    order.order_status = 'refunded'
    notify_payment_update(status='refunded')
```

### 4.3 Partial Refund Handling
```python
if transaction_status == 'partial_refund':
    payment.payment_status = 'partial_refund'
```

---

## 5. Order Lifecycle (Payment-Related)

```
PENDING → PAID → PROCESSED → SHIPPED → COMPLETED
                          ↘
                     CANCELLED / REFUNDED
```

**Payment status transitions:**
- `pending` → Initial state after Snap token created
- `paid` → After settlement webhook received
- `failed` → After deny webhook
- `cancelled` → After cancel webhook
- `expired` → After expire webhook
- `refunded` → After refund webhook
- `partial_refund` → After partial refund webhook
- `challenge` → After fraud challenge webhook
- `chargeback` → After chargeback webhook

---

## 6. Notification Triggers (Post-Payment)

| Event | Notification Type | Recipient | Channel |
|-------|------------------|-----------|---------|
| Payment successful | `payment` | Buyer | DB + WebSocket |
| Order paid (seller alert) | `order_update` | Seller | WebSocket |
| Payment failed | `payment` | Buyer | DB + WebSocket |
| Refund completed | `payment` | Buyer | DB + WebSocket |
| Chargeback initiated | `payment` | Admin | DB + WebSocket |

---

## 7. AI Recommendation Triggers

After successful payment, the following AI features are triggered:
1. **MarketplaceHealthSnapshot** — Updated with new transaction metrics
2. **DigitalTwin** — Buyer persona and CLV predictions recalculated
3. **DemandPrediction** — Product demand forecasts updated
4. **EngagementProfile** — Buyer engagement metrics updated
5. **ChurnPrediction** — Churn risk recalculated (paid buyers less likely to churn)

---

## 8. Celery Task Flow

```python
@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def create_snap_transaction_task(self, order_id, payment_method, bank=None):
    # 1. Load order from DB
    # 2. Build Midtrans payload
    # 3. POST to Midtrans Snap API
    # 4. Parse response
    # 5. Create/update Payment + MidtransTransaction records
    # 6. Return Snap token and redirect URL
```

---

## 9. Admin Payment Monitoring

**Available endpoints for admin monitoring:**
| Endpoint | Purpose |
|----------|---------|
| `/api/payments/history/` | User payment history |
| `/api/payments/status/{order_id}/` | Payment status lookup |
| `/api/payments/finance/summary/` | Seller finance summary |
| `/api/payments/finance/transactions/` | Seller finance ledger |

**Recommended admin additions (not yet implemented):**
- `/admin/monitoring/payments/` — All transactions dashboard
- `/admin/monitoring/webhooks/` — Webhook delivery log
- `/admin/monitoring/reconciliation/` — Manual reconciliation tool
- `/admin/monitoring/disputes/` — Chargeback and fraud tracking

---

## 10. WebSocket Real-Time Updates

```python
def notify_payment_update(user_id, order_id, order_number, payment_status, message=''):
    channel_layer.group_send(
        f'notifications_{user_id}',
        {
            'type': 'payment_update',
            'order_id': order_id,
            'order_number': order_number,
            'status': payment_status,
            'message': message,
        }
    )
```

Real-time updates sent for:
1. ✅ Payment success (buyer + seller)
2. ✅ Payment failure (buyer)
3. ✅ Refund/chargeback (buyer)
4. ✅ Order status change (seller)

---

## 11. Payment Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        BUYER CHECKOUT FLOW                            │
├────────────┬──────────────────┬──────────────┬───────────────────────┤
│  FRONTEND  │    DJANGO API    │  MIDTRANS    │      DATABASE          │
├────────────┼──────────────────┼──────────────┼───────────────────────┤
│            │                  │              │                       │
│  Cart      │                  │              │  Cart items           │
│    │       │                  │              │                       │
│    ▼       │                  │              │                       │
│  Checkout  │                  │              │                       │
│  Form      │                  │              │                       │
│    │       │                  │              │                       │
│    ├───────┤ POST /orders/   │              │  Order (pending)      │
│    │       │──────────────────▶              ├──────▶ Created         │
│    │       │◀─────────────────┤              │                       │
│    │       │  OrderResponse    │              │                       │
│    │       │                  │              │                       │
│    ├───────┤ POST /create-snap│              │                       │
│    │       │──────────────────┬──────────────► Snap API              │
│    │       │                  │  Snap Token  │                       │
│    │       │◀─────────────────┼──────────────┤                       │
│    │       │  SnapResponse    │              │  Payment (pending)    │
│    │       │                  │              ├──────▶ Created         │
│    ▼       │                  │              │  MidtransTxn (pending)│
│  Snap      │                  │              ├──────▶ Created         │
│  Popup     │                  │              │                       │
│    │       │                  │              │                       │
│    ▼       │                  │              │                       │
│  Payment   │                  │              │                       │
│  Complete  │                  │          ◄───┤ Buyer pays            │
│    │       │                  │              │                       │
│    │       │                  │  Webhook     │                       │
│    │       │◀─────────────────┼──────────────┤                       │
│    │       │  POST /notification/            │                       │
│    │       │──────────────────┤              │  Payment → paid       │
│    │       │  Verify Sig,     │              ├──────▶ Updated         │
│    │       │  Dedup, Update   │              │  Order → paid         │
│    │       │                  │              ├──────▶ Updated         │
│    ▼       │                  │              │  AdminFeeTxn created  │
│  Success   │  Status OK       │              ├──────▶ Created         │
│    ◄───────┤──────────────────┤              │                       │
│            │                  │              │                       │
└────────────┴──────────────────┴──────────────┴───────────────────────┘
```
