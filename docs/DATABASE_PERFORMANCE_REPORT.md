# Database Performance Report — Warungio Marketplace

**Date:** July 20, 2026

---

## 1. Query Patterns

| Pattern | Frequency | Performance Impact |
|---------|-----------|-------------------|
| `.values()` / `.values_list()` | 62 uses | ✅ Avoids model instantiation |
| `select_related()` | Multiple views | ✅ Single query for FK joins |
| `prefetch_related()` | Multiple views | ✅ Two queries for M2M/reverse |
| `annotate()` | Analytics views | ✅ Aggregation in DB |
| `bulk_create()` | Seed scripts | ✅ Fast batch inserts |

## 2. Database Indexing

| Table | Model | Fields | Indexes | Status |
|-------|-------|--------|---------|--------|
| users | accounts.User | 84 | 5 | ⚠️ Large table, consider composite indexes |
| stores_store | stores.Store | 57 | 4 | ✅ |
| products_product | products.Product | 31 | 5 | ✅ |
| orders_order | orders.Order | 32 | 4 | ✅ |
| suppliers_supplier | suppliers.Supplier | 52 | 6 | ✅ |

## 3. Index Analysis

### Existing Indexes (examples)
- `accounts.User`: `email` (unique), `phone` (unique), `role`, `is_verified`, `created_at`
- `products.Product`: `store_id`, `category_id`, `slug` (unique), `is_active`, `created_at`
- `orders.Order`: `buyer_id`, `store_id`, `status`, `created_at`

### Recommended Additional Indexes

| Table | Columns | Reason |
|-------|---------|--------|
| `orders.Order` | `(store_id, status, created_at)` | Seller dashboard queries |
| `products.Product` | `(category_id, price, is_active)` | Category browsing with price sort |
| `notifications.Notification` | `(recipient_id, is_read, created_at)` | Unread notification count |
| `analytics.SalesAnalytics` | `(store_id, date)` | Sales trend queries |
| `inventory.ProductBatch` | `(product_id, expiry_date)` | FEFO expiry checks |

## 4. Connection Pooling

| Setting | Value | Impact |
|---------|-------|--------|
| `CONN_MAX_AGE` | 60s | ✅ Reduces TCP handshake overhead |
| Max connections (MariaDB) | 30 (config) | ✅ Within 1GB RAM budget |
| Pool type | Per-process persistent | ✅ Standard Django |

## 5. Query Execution Time Estimates

| Query Type | Estimated Time | Data Volume |
|-----------|---------------|-------------|
| Single row lookup (PK) | <1ms | N/A |
| FK join (2 tables) | 2-10ms | 100K rows |
| Filtered list (paginated) | 10-50ms | 50K rows, 20/page |
| Aggregation (COUNT, SUM) | 20-100ms | 10K-100K rows |
| Full text search (LIKE) | 50-500ms | 100K rows |
| Report generation | 500ms-5s | 1M+ rows across 5 tables |

## 6. Migration Health

| Check | Result |
|-------|--------|
| Unapplied migrations | ✅ None |
| Fake migrations | ✅ None |
| Migration conflicts | ✅ None |
| `makemigrations --check` | ✅ No changes |

## 7. Recommendations

1. **Add composite indexes** for most common query patterns (dashboard, notifications)
2. **Monitor slow query log** (`long_query_time=1`) in production
3. **Increase `innodb_buffer_pool_size`** to 128 MB if RAM allows
4. **Consider table partitioning** for `analytics_salesanalytics` if >10M rows
