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
"""

from django.db import migrations


class Migration(migrations.Migration):
    """Add performance indexes for payments and wallet transactions."""

    dependencies = [
        ('payments', '0006_repair_missing_wallet_tables'),
    ]

    operations = [
        # Composite index for user payment history + status filter
        migrations.RunSQL(
            sql=(
                "CREATE INDEX payments_user_status_idx "
                "ON payments (user_id, payment_status)"
            ),
            reverse_sql=(
                "ALTER TABLE payments DROP INDEX payments_user_status_idx"
            ),
        ),
        # Composite index for withdrawal queries (FinanceTransactionListView)
        migrations.RunSQL(
            sql=(
                "CREATE INDEX payments_user_type_status_idx "
                "ON payments (user_id, payment_type, payment_status)"
            ),
            reverse_sql=(
                "ALTER TABLE payments DROP INDEX payments_user_type_status_idx"
            ),
        ),
        # Index for date-range payment filtering
        migrations.RunSQL(
            sql=(
                "CREATE INDEX payments_created_idx "
                "ON payments (created_at)"
            ),
            reverse_sql=(
                "ALTER TABLE payments DROP INDEX payments_created_idx"
            ),
        ),
        # Composite index for wallet idempotency lookups
        # Speeds up: SELECT * FROM wallet_transactions WHERE reference_type=? AND reference_id=?
        migrations.RunSQL(
            sql=(
                "CREATE INDEX wallet_tx_ref_idx "
                "ON wallet_transactions (reference_type, reference_id(50))"
            ),
            reverse_sql=(
                "ALTER TABLE wallet_transactions DROP INDEX wallet_tx_ref_idx"
            ),
        ),
        # Composite index for wallet transaction history by type
        migrations.RunSQL(
            sql=(
                "CREATE INDEX wallet_tx_user_type_idx "
                "ON wallet_transactions (user_id, tx_type, created_at)"
            ),
            reverse_sql=(
                "ALTER TABLE wallet_transactions DROP INDEX wallet_tx_user_type_idx"
            ),
        ),
        # Index for admin fee payout queue filtering
        migrations.RunSQL(
            sql=(
                "CREATE INDEX admin_fee_payout_status_idx "
                "ON admin_fee_transactions (payout_status)"
            ),
            reverse_sql=(
                "ALTER TABLE admin_fee_transactions DROP INDEX admin_fee_payout_status_idx"
            ),
        ),
        # Composite index for store-level admin fee summary
        migrations.RunSQL(
            sql=(
                "CREATE INDEX admin_fee_store_created_idx "
                "ON admin_fee_transactions (store_id, created_at)"
            ),
            reverse_sql=(
                "ALTER TABLE admin_fee_transactions DROP INDEX admin_fee_store_created_idx"
            ),
        ),
    ]
