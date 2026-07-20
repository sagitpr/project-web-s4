"""
Repair migration: Add missing columns to quality_checks table.

Migration 0002_qualitycheck is recorded as applied but the physical
table lacks columns `quality_status` and `created_at` that the
current QualityCheck model requires.

This forward-only repair adds those columns only if they are
missing, preserving all existing data.
"""

from django.db import migrations, models


def add_missing_quality_columns(apps, schema_editor):
    """Add quality_status and created_at columns if they don't exist."""
    with schema_editor.connection.cursor() as cursor:
        # Check current columns
        cursor.execute("PRAGMA table_info('quality_checks')")
        columns = {row[1] for row in cursor.fetchall()}

        if 'quality_status' not in columns:
            cursor.execute(
                "ALTER TABLE quality_checks ADD COLUMN "
                "quality_status varchar(20) NOT NULL DEFAULT 'pending'"
            )
            print("  [+] Added quality_status column to quality_checks")

        if 'created_at' not in columns:
            cursor.execute(
                "ALTER TABLE quality_checks ADD COLUMN "
                "created_at datetime(6) NOT NULL DEFAULT '2026-01-01 00:00:00'"
            )
            print("  [+] Added created_at column to quality_checks")


class Migration(migrations.Migration):
    """Forward-only repair for quality_checks missing columns."""

    dependencies = [
        ('products', '0006_product_reserved_stock'),
    ]

    operations = [
        migrations.RunPython(
            add_missing_quality_columns,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
