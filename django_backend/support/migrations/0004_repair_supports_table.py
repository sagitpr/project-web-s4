"""
Repair migration: Create the missing `supports` table.

Migration 0003_supportticket is recorded as applied but the physical
`supports` table does not exist in the database. This forward-only
repair creates the table only if missing, preserving all existing data.
"""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def create_supports_table_if_missing(apps, schema_editor):
    """Create the supports table if it doesn't exist in the database."""
    with schema_editor.connection.cursor() as cursor:
        # Check if table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='supports'"
        )
        if cursor.fetchone():
            print("  [+] supports table already exists, skipping creation")
            return

        # Table doesn't exist — create it with all required columns
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "supports" (
                "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
                "subject" varchar(255) NOT NULL,
                "message" text NOT NULL,
                "support_status" varchar(20) NOT NULL DEFAULT 'open',
                "priority" varchar(20) NOT NULL DEFAULT 'normal',
                "created_at" datetime(6) NOT NULL,
                "updated_at" datetime(6) NOT NULL,
                "user_id" bigint NULL REFERENCES "users"("id") ON DELETE SET NULL
            )
        """)
        print("  [+] Created supports table")

        # Create indexes (matching the original migration)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS "supports_user_id_b14d68_idx"
            ON "supports" ("user_id")
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS "supports_support_6dae3e_idx"
            ON "supports" ("support_status")
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS "supports_created_ad314a_idx"
            ON "supports" ("created_at")
        """)
        print("  [+] Created indexes for supports table")


class Migration(migrations.Migration):
    """Forward-only repair for missing supports table."""

    dependencies = [
        ('support', '0003_supportticket'),
    ]

    operations = [
        migrations.RunPython(
            create_supports_table_if_missing,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
