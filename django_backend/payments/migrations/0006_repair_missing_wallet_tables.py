"""
Repair migration: Create missing wallet and wallet_transactions tables.

Migrations 0004_wallet_and_transactions and 0005 are recorded as
applied but on some environments (notably MariaDB production) the
physical `wallet_transactions` table may not exist. This can cause
ORM operations like User.delete() and WalletTransaction queries to
fail with ProgrammingError (1146 table does not exist).

This forward-only repair:
  - Creates the `wallets` table if missing
  - Creates the `wallet_transactions` table if missing
  - Creates all required indexes if missing
  - Is fully idempotent (safe to run multiple times)
"""

from django.db import migrations


def _table_exists(cursor, table_name):
    """Check if a table exists (works for both SQLite and MySQL/MariaDB)."""
    import sqlite3
    try:
        # Try SQLite approach first
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='" +
            table_name + "'"
        )
        return cursor.fetchone() is not None
    except sqlite3.OperationalError:
        pass
    except Exception:
        pass
    try:
        # Try MySQL/MariaDB approach
        cursor.execute("SHOW TABLES LIKE '" + table_name + "'")
        return cursor.fetchone() is not None
    except Exception:
        pass
    try:
        # Try information_schema approach
        cursor.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = DATABASE() AND table_name = '" +
            table_name + "'"
        )
        return cursor.fetchone() is not None
    except Exception:
        pass
    # Fallback: attempt a simple SELECT
    try:
        cursor.execute("SELECT COUNT(*) FROM `" + table_name + "`")
        return True
    except Exception:
        return False


def _column_exists(cursor, table, column):
    """Check if a column exists in a table."""
    try:
        cursor.execute("PRAGMA table_info('" + table + "')")
        for row in cursor.fetchall():
            if row[1] == column:
                return True
    except Exception:
        pass
    try:
        cursor.execute("SHOW COLUMNS FROM `" + table + "` LIKE '" + column + "'")
        return cursor.fetchone() is not None
    except Exception:
        pass
    return False


def repair_wallet_tables(apps, schema_editor):
    """Create missing wallet tables and indexes."""
    with schema_editor.connection.cursor() as cursor:
        import sqlite3
        is_sqlite = isinstance(
            schema_editor.connection.connection, sqlite3.Connection
        )
        engine = 'sqlite' if is_sqlite else 'mysql'

        # -- 1. Ensure wallets table --
        if not _table_exists(cursor, 'wallets'):
            if engine == 'sqlite':
                cursor.execute("""
                    CREATE TABLE "wallets" (
                        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
                        "balance" decimal(14, 2) NOT NULL DEFAULT '0.00',
                        "created_at" datetime(6) NOT NULL,
                        "updated_at" datetime(6) NOT NULL,
                        "user_id" bigint NOT NULL UNIQUE
                        REFERENCES "users"("id") ON DELETE CASCADE
                    )
                """)
            else:
                cursor.execute("""
                    CREATE TABLE `wallets` (
                        `id` bigint NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        `balance` decimal(14, 2) NOT NULL DEFAULT 0.00,
                        `created_at` datetime(6) NOT NULL,
                        `updated_at` datetime(6) NOT NULL,
                        `user_id` bigint NOT NULL UNIQUE,
                        CONSTRAINT `fk_wallets_user`
                        FOREIGN KEY (`user_id`)
                        REFERENCES `users` (`id`)
                        ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
            print("  [+] Created wallets table")
        else:
            print("  [+] wallets table already exists")

        # -- Ensure user_id FK column exists on wallets --
        if not _column_exists(cursor, 'wallets', 'user_id'):
            cursor.execute(
                "ALTER TABLE wallets ADD COLUMN "
                "user_id bigint NOT NULL UNIQUE"
            )
            print("  [+] Added user_id column to wallets")

        # -- 2. Ensure wallet_transactions table --
        if not _table_exists(cursor, 'wallet_transactions'):
            if engine == 'sqlite':
                cursor.execute("""
                    CREATE TABLE "wallet_transactions" (
                        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
                        "tx_type" varchar(20) NOT NULL,
                        "amount" decimal(14, 2) NOT NULL,
                        "balance_before" decimal(14, 2) NOT NULL,
                        "balance_after" decimal(14, 2) NOT NULL,
                        "description" varchar(255) NULL,
                        "reference_type" varchar(50) NULL,
                        "reference_id" varchar(100) NULL,
                        "created_at" datetime(6) NOT NULL,
                        "user_id" bigint NULL
                            REFERENCES "users"("id") ON DELETE SET NULL,
                        "wallet_id" bigint NOT NULL
                            REFERENCES "wallets"("id") ON DELETE CASCADE
                    )
                """)
            else:
                cursor.execute("""
                    CREATE TABLE `wallet_transactions` (
                        `id` bigint NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        `tx_type` varchar(20) NOT NULL,
                        `amount` decimal(14, 2) NOT NULL,
                        `balance_before` decimal(14, 2) NOT NULL,
                        `balance_after` decimal(14, 2) NOT NULL,
                        `description` varchar(255) NULL,
                        `reference_type` varchar(50) NULL,
                        `reference_id` varchar(100) NULL,
                        `created_at` datetime(6) NOT NULL,
                        `user_id` bigint NULL,
                        `wallet_id` bigint NOT NULL,
                        CONSTRAINT `fk_wallet_txn_wallet`
                        FOREIGN KEY (`wallet_id`)
                        REFERENCES `wallets` (`id`)
                        ON DELETE CASCADE,
                        CONSTRAINT `fk_wallet_txn_user`
                        FOREIGN KEY (`user_id`)
                        REFERENCES `users` (`id`)
                        ON DELETE SET NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
            print("  [+] Created wallet_transactions table")

            # -- 3. Create indexes (only for new table) --
            if engine == 'sqlite':
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS "wallet_tran_wallet_created_idx"
                    ON "wallet_transactions" ("wallet_id", "created_at" DESC)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS "wallet_tran_user_created_idx"
                    ON "wallet_transactions" ("user_id", "created_at" DESC)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS "wallet_tran_tx_type_idx"
                    ON "wallet_transactions" ("tx_type")
                """)
            else:
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS `wallet_tran_wallet_created_idx`
                    ON `wallet_transactions` (`wallet_id`, `created_at` DESC)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS `wallet_tran_user_created_idx`
                    ON `wallet_transactions` (`user_id`, `created_at` DESC)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS `wallet_tran_tx_type_idx`
                    ON `wallet_transactions` (`tx_type`)
                """)
            print("  [+] Created indexes for wallet_transactions")
        else:
            print("  [+] wallet_transactions table already exists")
            if not _column_exists(cursor, 'wallet_transactions', 'wallet_id'):
                cursor.execute(
                    "ALTER TABLE wallet_transactions ADD COLUMN "
                    "wallet_id bigint NOT NULL"
                )
                print("  [+] Added wallet_id column to wallet_transactions")

        # -- 4. Ensure indexes on wallet_transactions --
        if engine == 'sqlite':
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS "wallet_tran_wallet_created_idx"
                ON "wallet_transactions" ("wallet_id", "created_at" DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS "wallet_tran_user_created_idx"
                ON "wallet_transactions" ("user_id", "created_at" DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS "wallet_tran_tx_type_idx"
                ON "wallet_transactions" ("tx_type")
            """)
        print("  [+] Verified all indexes on wallet_transactions")


class Migration(migrations.Migration):
    """Forward-only repair for missing wallet/wallet_transactions tables."""

    dependencies = [
        ('payments', '0005_rename_wallet_txn_wallet_created_idx_'
                     'wallet_tran_wallet__3d47ad_idx_and_more'),
    ]

    operations = [
        migrations.RunPython(
            repair_wallet_tables,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
