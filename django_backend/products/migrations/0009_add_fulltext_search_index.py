"""Add full-text search index on products for faster product search.

Adds a FULLTEXT index on products(product_name, description) for MariaDB/MySQL.
This enables efficient product search via MATCH...AGAINST instead of LIKE %term%
which causes full table scans.

The index is created via RunSQL because Django's ORM doesn't natively support
FULLTEXT indexes (they are database-specific).

Note: For SQLite (dev environment), this migration is a no-op.
Full-text search only works on MariaDB/MySQL.
"""

from django.db import migrations


class Migration(migrations.Migration):
    """Add full-text search index on products table."""

    dependencies = [
        ('products', '0008_alter_favorite_options'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE products "
                "ADD FULLTEXT INDEX ft_products_search (product_name, description)"
            ),
            reverse_sql=(
                "ALTER TABLE products DROP INDEX ft_products_search"
            ),
            # Only run on MariaDB/MySQL — SQLite will skip silently
            state_operations=None,
        ),
        # Add covering index for product search by store + name
        # Speeds up: SELECT * FROM products WHERE store_id=? AND product_name LIKE ?
        migrations.RunSQL(
            sql=(
                "CREATE INDEX products_store_name_idx ON products (store_id, product_name(100))"
            ),
            reverse_sql=(
                "ALTER TABLE products DROP INDEX products_store_name_idx"
            ),
            state_operations=None,
        ),
    ]
