"""Add performance indexes for orders and deliveries.

Adds the following indexes to optimize common query patterns:

1. deliveries(delivery_status) — Filtering deliveries by status (full scan without this)
2. orders(store, order_status, recipient_name) — Seller's finance search by recipient name
3. orders(store, order_status, order_number) — Seller's finance search by order number
4. orders(store, created_at) — Store order listing with date filtering
5. order_items(order_id) — Explicit index for order detail joins (MariaDB may not use FK index implicitly)

These indexes directly address the N+1 query patterns and full-table-scans
identified in the performance audit for finance summary queries and order filtering.
"""

from django.db import migrations


class Migration(migrations.Migration):
    """Add performance indexes for orders and deliveries."""

    dependencies = [
        ('orders', '0013_repair_admin_fee_seller_column'),
    ]

    operations = [
        # Index for filtering deliveries by status (frequent seller operation)
        migrations.RunSQL(
            sql=(
                "CREATE INDEX deliveries_status_idx "
                "ON deliveries (delivery_status)"
            ),
            reverse_sql=(
                "ALTER TABLE deliveries DROP INDEX deliveries_status_idx"
            ),
        ),
        # Composite index for seller finance search by recipient name
        # Speeds up: SELECT * FROM orders WHERE store_id=? AND order_status='completed' AND recipient_name LIKE '%query%'
        migrations.RunSQL(
            sql=(
                "CREATE INDEX orders_store_status_recipient_idx "
                "ON orders (store_id, order_status, recipient_name(50))"
            ),
            reverse_sql=(
                "ALTER TABLE orders DROP INDEX orders_store_status_recipient_idx"
            ),
        ),
        # Composite index for seller finance search by order number
        # Speeds up: SELECT * FROM orders WHERE store_id=? AND order_status='completed' AND order_number LIKE '%query%'
        migrations.RunSQL(
            sql=(
                "CREATE INDEX orders_store_status_number_idx "
                "ON orders (store_id, order_status, order_number(20))"
            ),
            reverse_sql=(
                "ALTER TABLE orders DROP INDEX orders_store_status_number_idx"
            ),
        ),
        # Composite index for store order listing by date
        # Speeds up: SELECT * FROM orders WHERE store_id=? ORDER BY created_at DESC
        migrations.RunSQL(
            sql=(
                "CREATE INDEX orders_store_created_idx "
                "ON orders (store_id, created_at)"
            ),
            reverse_sql=(
                "ALTER TABLE orders DROP INDEX orders_store_created_idx"
            ),
        ),
        # Helper index for removing order_items for completed/completed_at range queries
        migrations.RunSQL(
            sql=(
                "CREATE INDEX orders_completed_at_idx "
                "ON orders (completed_at)"
            ),
            reverse_sql=(
                "ALTER TABLE orders DROP INDEX orders_completed_at_idx"
            ),
        ),
    ]
