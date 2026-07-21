"""Add performance indexes for orders and deliveries.

Adds the following indexes to optimize common query patterns:

1. deliveries(delivery_status) — Filtering deliveries by status (full scan without this)
2. orders(store, order_status, recipient_name) — Seller's finance search by recipient name
3. orders(store, order_status, order_number) — Seller's finance search by order number
4. orders(store, created_at) — Store order listing with date filtering
5. orders(completed_at) — Finance/reporting date range queries

Uses RunSQL (not AddIndex) because these are performance-only indexes that
should NOT be tracked in Django's ORM migration state. Adding them via AddIndex
would require model Meta.indexes updates which would generate false migration changes.

MySQL compatibility: Original used prefix-length syntax (recipient_name(50)) which
is MySQL-specific and breaks SQLite test databases. Prefix lengths removed for
cross-DB compatibility — functionally equivalent on both engines.
"""

from django.db import migrations


class Migration(migrations.Migration):
    """Add performance indexes for orders and deliveries."""

    dependencies = [
        ('orders', '0013_repair_admin_fee_seller_column'),
    ]

    operations = [
        # Index for filtering deliveries by status (frequent seller operation)
        # Table name: deliveries (from Delivery.Meta.db_table)
        migrations.RunSQL(
            sql=(
                "CREATE INDEX IF NOT EXISTS deliveries_status_idx "
                "ON deliveries (delivery_status)"
            ),
            reverse_sql=(
                "DROP INDEX IF EXISTS deliveries_status_idx"
            ),
        ),
        # Composite index for seller finance search by recipient name
        # Speeds up: SELECT * FROM orders WHERE store_id=? AND order_status='completed' AND recipient_name LIKE '%query%'
        # Table name: orders (from Order.Meta.db_table)
        # NOTE: Prefix-length syntax (recipient_name(50)) is MySQL-specific.
        # SQLite doesn't support it, so we use recipient_name without prefix length.
        migrations.RunSQL(
            sql=(
                "CREATE INDEX IF NOT EXISTS orders_store_status_recipient_idx "
                "ON orders (store_id, order_status, recipient_name)"
            ),
            reverse_sql=(
                "DROP INDEX IF EXISTS orders_store_status_recipient_idx"
            ),
        ),
        # Composite index for seller finance search by order number
        # Speeds up: SELECT * FROM orders WHERE store_id=? AND order_status='completed' AND order_number LIKE '%query%'
        # NOTE: order_number(20) prefix removed for SQLite compatibility
        migrations.RunSQL(
            sql=(
                "CREATE INDEX IF NOT EXISTS orders_store_status_number_idx "
                "ON orders (store_id, order_status, order_number)"
            ),
            reverse_sql=(
                "DROP INDEX IF EXISTS orders_store_status_number_idx"
            ),
        ),
        # Composite index for store order listing by date
        # Speeds up: SELECT * FROM orders WHERE store_id=? ORDER BY created_at DESC
        migrations.RunSQL(
            sql=(
                "CREATE INDEX IF NOT EXISTS orders_store_created_idx "
                "ON orders (store_id, created_at)"
            ),
            reverse_sql=(
                "DROP INDEX IF EXISTS orders_store_created_idx"
            ),
        ),
        # Index for filtering orders by completed_at (finance/reporting queries)
        # Speeds up: SELECT * FROM orders WHERE completed_at BETWEEN ? AND ?
        migrations.RunSQL(
            sql=(
                "CREATE INDEX IF NOT EXISTS orders_completed_at_idx "
                "ON orders (completed_at)"
            ),
            reverse_sql=(
                "DROP INDEX IF EXISTS orders_completed_at_idx"
            ),
        ),
    ]
