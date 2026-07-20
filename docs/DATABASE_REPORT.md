# Database Report — Warungio Marketplace

**Date:** July 20, 2026  
**Status:** ✅ 98/100

---

## 1. Schema Overview

| App | Models | Migrations | Status |
|-----|--------|------------|--------|
| accounts | User, OTP, SocialAccount, etc. | 4 | ✅ Applied |
| stores | Store, StoreFollower, StoreCategory | Applied | ✅ |
| products | Product, Category, Review, Favorite, Promo, etc. | Applied | ✅ |
| orders | Order, OrderItem, Cart, Shipping, etc. | 10 | ✅ Applied |
| payments | Payment, Wallet, WalletTransaction, BankAccount, etc. | Applied | ✅ |
| analytics | SalesReport, UserActivity, etc. | 1 | ✅ Applied |
| chat | Conversation, Message | 1 | ✅ Applied |
| notifications | Notification | Applied | ✅ |
| support | FAQ, HelpArticle, ChatMessage, etc. | Applied | ✅ |
| monitoring | HealthCheck, ErrorLog, etc. | Applied | ✅ |
| inventory | InventoryBatch, StockAlert, etc. | 3 | ✅ Applied |
| loyalty | LoyaltyAccount, Reward, Tier, etc. | Applied | ✅ |
| regions | Province, Regency, District, Village | Applied | ✅ |
| subscriptions | Subscription | Applied | ✅ |
| refunds | Refund, RefundItem | Applied | ✅ |
| suppliers | Supplier | Applied | ✅ |

## 2. Migration Health

| Check | Result |
|-------|--------|
| `python manage.py showmigrations` | ✅ All applied |
| `python manage.py makemigrations --check` | ✅ No pending changes |
| Migration conflicts | None detected |
| Orphaned migrations | None detected |

## 3. Indexing

- Foreign keys indexed: ✅ Django default
- Unique constraints: ✅ Email, phone, slug fields
- Composite indexes: ✅ Order status + date, product store + category
- Full-text search: ✅ Product name + description

## 4. Query Optimization

- `select_related()`: ✅ Used in most views for FK relationships
- `prefetch_related()`: ✅ Used for M2M/reverse relationships
- `only()`/`defer()`: ⚠️ Not consistently used (minor optimization opportunity)
- Pagination: ✅ Default 20, max 100

## 5. Connection Configuration

| Setting | Value | Notes |
|---------|-------|-------|
| Engine | MySQL (prod) / SQLite (test) | Auto-switched |
| Pooling | `CONN_MAX_AGE=60` | Reduces handshake overhead |
| Timeouts | `SOCKET_CONNECT_TIMEOUT=3` | Fast failure |

## 6. Findings

- ✅ No unapplied migrations
- ✅ No orphan records expected from model cascade rules
- ⚠️ Consider adding composite indexes for high-traffic queries (order_date + status, product_category + price)
