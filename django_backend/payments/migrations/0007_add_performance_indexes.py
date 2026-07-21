"""Add performance indexes for payments and wallet transactions.

Adds indexes for:

1. payments(user, payment_status) — User payment history filtering
2. payments(user, payment_type, payment_status) — Withdrawal queries for seller finance
3. payments(created_at) — Date-range filtering
4. wallet_transactions(user, tx_type, created_at) — User wallet history filtering
5. wallet_transactions(reference_type, reference_id) — Idempotency lookup for wallet operations
6. admin_fee_transactions(payout_status) — Admin payout queue filtering
7. admin_fee_transactions(store, created_at) — Store admin fee summary

These indexes directly address full-table-scans identified in the audit
for the FinanceSummaryView, FinanceTransactionListView, and WalletService operations.

SQLite compatibility: Original used MySQL-specific syntax:
- prefix-length index (reference_id(50)) — SQLite interprets this as a function call
- ALTER TABLE ... DROP INDEX — MySQL syntax, SQLite uses DROP INDEX directly

Fixes applied:
- Removed prefix-length syntax for cross-DB compatibility
- Changed reverse_sql from ALTER TABLE ... DROP INDEX to DROP INDEX IF EXISTS
  (works on SQLite, MySQL 8.0+, MariaDB 10.0+)
- Added IF NOT EXISTS for idempotency on SQLite
"""

from django.db import migrations


class Migration(migrations.Migration):
    """Add performance indexes for payments and wallet transactions."""

    dependencies = [
        ('payments', '0006_repair_missing_wallet_tables'),
    ]

    operations = [
        # Composite index for user payment history + status filter
        # Table: payments (from Payment.Meta.db_table)
        migrations.RunSQL(
            sql=(
                "CREATE INDEX IF NOT EXISTS payments_user_status_idx "
                "ON payments (user_id, payment_status)"
            ),
            reverse_sql=(
                "DROP INDEX IF EXISTS payments_user_status_idx"
            ),
        ),
        # Composite index for withdrawal queries (FinanceTransactionListView)
        migrations.RunSQL(
            sql=(
                "CREATE INDEX IF NOT EXISTS payments_user_type_status_idx "
                "ON payments (user_id, payment_type, payment_status)"
            ),
            reverse_sql=(
                "DROP INDEX IF EXISTS payments_user_type_status_idx"
            ),
        ),
        # Index for date-range payment filtering
        migrations.RunSQL(
            sql=(
                "CREATE INDEX IF NOT EXISTS payments_created_idx "
                "ON payments (created_at)"
            ),
            reverse_sql=(
                "DROP INDEX IF EXISTS payments_created_idx"
            ),
        ),
        # Composite index for wallet idempotency lookups
        # Speeds up: SELECT * FROM wallet_transactions WHERE reference_type=? AND reference_id=?
        # Table: wallet_transactions (from WalletTransaction.Meta.db_table)
        # NOTE: reference_id(50) prefix-length syntax is MySQL-specific.
        # SQLite interprets it as a function call ("no such function: reference_id").
        # Using reference_id without prefix length for cross-DB compatibility.
        migrations.RunSQL(
            sql=(
                "CREATE INDEX IF NOT EXISTS wallet_tx_ref_idx "
                "ON wallet_transactions (reference_type, reference_id)"
            ),
            reverse_sql=(
                "DROP INDEX IF EXISTS wallet_tx_ref_idx"
            ),
        ),
        # Composite index for wallet transaction history by type
        migrations.RunSQL(
            sql=(
                "CREATE INDEX IF NOT EXISTS wallet_tx_user_type_idx "
                "ON wallet_transactions (user_id, tx_type, created_at)"
            ),
            reverse_sql=(
                "DROP INDEX IF EXISTS wallet_tx_user_type_idx"
            ),
        ),
        # Index for admin fee payout queue filtering
        # Table: admin_fee_transactions (from AdminFeeTransaction.Meta.db_table)
        migrations.RunSQL(
            sql=(
                "CREATE INDEX IF NOT EXISTS admin_fee_payout_status_idx "
                "ON admin_fee_transactions (payout_status)"
            ),
            reverse_sql=(
                "DROP INDEX IF EXISTS admin_fee_payout_status_idx"
            ),
        ),
        # Composite index for store-level admin fee summary
        migrations.RunSQL(
            sql=(
                "CREATE INDEX IF NOT EXISTS admin_fee_store_created_idx "
                "ON admin_fee_transactions (store_id, created_at)"
            ),
            reverse_sql=(
                "DROP INDEX IF EXISTS admin_fee_store_created_idx"
            ),
        ),
    ]
