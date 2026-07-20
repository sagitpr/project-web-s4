"""
Repair migration: Add missing admin_fee_seller column to orders table.

Migration 0012_alter_order_admin_fee_seller is recorded as applied
but the physical `orders` table lacks the `admin_fee_seller` column
that the current Order model requires.

This forward-only repair adds the column only if missing,
preserving all existing data.
"""

from decimal import Decimal

from django.db import migrations, models


def add_admin_fee_seller_column(apps, schema_editor):
    """Add admin_fee_seller column if it doesn't exist."""
    with schema_editor.connection.cursor() as cursor:
        # Check current columns
        cursor.execute("PRAGMA table_info('orders')")
        columns = {row[1] for row in cursor.fetchall()}

        if 'admin_fee_seller' not in columns:
            cursor.execute(
                "ALTER TABLE orders ADD COLUMN "
                "admin_fee_seller decimal(10, 2) NOT NULL DEFAULT '1000.00'"
            )
            print("  [+] Added admin_fee_seller column to orders")


class Migration(migrations.Migration):
    """Forward-only repair for orders missing admin_fee_seller column."""

    dependencies = [
        ('orders', '0012_alter_order_admin_fee_seller'),
    ]

    operations = [
        migrations.RunPython(
            add_admin_fee_seller_column,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
