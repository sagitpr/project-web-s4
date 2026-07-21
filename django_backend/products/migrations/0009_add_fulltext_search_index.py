"""Add search indexes on products for faster product search.

Adds indexes for:

1. products(product_name, description) — Composite B-tree index for product search
2. products(store_id, product_name) — Covering index for store-scoped product search

Originally used MySQL-only FULLTEXT index and prefix-length syntax.
Migrated to standard B-tree indexes for cross-DB compatibility.

SQLite compatibility: Original used:
- ALTER TABLE ... ADD FULLTEXT INDEX — MySQL-specific, fails on SQLite
- product_name(100) — prefix-length syntax, SQLite interprets as function call
- ALTER TABLE ... DROP INDEX — MySQL-specific reverse SQL
- state_operations=None — invalid parameter for RunSQL

Fixes applied:
- Replaced FULLTEXT with standard composite B-tree index (works on all DB engines)
- Removed prefix-length syntax (product_name(100) → product_name)
- Added IF NOT EXISTS for idempotency on SQLite
- Changed reverse_sql to DROP INDEX IF EXISTS
- Removed invalid state_operations parameter
"""

from django.db import migrations


class Migration(migrations.Migration):
    """Add search indexes on products table."""

    dependencies = [
        ('products', '0008_alter_favorite_options'),
    ]

    operations = [
        # Composite B-tree index for product name + description search
        # Replaces MySQL-only FULLTEXT index for cross-DB compatibility.
        # Speeds up: SELECT * FROM products WHERE product_name LIKE '%term%'
        #           SELECT * FROM products WHERE product_name LIKE 'term%'
        # Table: products (from Product.Meta.db_table)
        migrations.RunSQL(
            sql=(
                "CREATE INDEX IF NOT EXISTS ft_products_search "
                "ON products (product_name, description)"
            ),
            reverse_sql=(
                "DROP INDEX IF EXISTS ft_products_search"
            ),
        ),
        # Composite index for product search by store + name
        # Speeds up: SELECT * FROM products WHERE store_id=? AND product_name LIKE ?
        # NOTE: product_name(100) prefix-length syntax removed for SQLite compatibility
        migrations.RunSQL(
            sql=(
                "CREATE INDEX IF NOT EXISTS products_store_name_idx "
                "ON products (store_id, product_name)"
            ),
            reverse_sql=(
                "DROP INDEX IF EXISTS products_store_name_idx"
            ),
        ),
    ]
