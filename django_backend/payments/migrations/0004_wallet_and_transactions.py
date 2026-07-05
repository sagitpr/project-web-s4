'''Migration: Create Wallet and WalletTransaction tables (idempotent).

Gunakan SeparateDatabaseAndState + CREATE TABLE IF NOT EXISTS agar:
- Jika tabel sudah ada (error 1050): RUNSQL tidak melakukan apa-apa, state tetap sinkron
- Jika tabel belum ada: RUNSQL membuat tabel, state tetap sinkron
- Data pengguna di tabel yang sudah ada TIDAK akan terhapus
'''

from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


CREATE_WALLETS_SQL = '''
CREATE TABLE IF NOT EXISTS `wallets` (
    `id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `balance` decimal(14, 2) NOT NULL DEFAULT 0,
    `created_at` datetime(6) NOT NULL,
    `updated_at` datetime(6) NOT NULL,
    `user_id` bigint NOT NULL UNIQUE,
    CONSTRAINT `fk_wallets_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
'''

CREATE_WALLET_TXNS_SQL = '''
CREATE TABLE IF NOT EXISTS `wallet_transactions` (
    `id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY,
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
    INDEX `wallet_txn_wallet_created_idx` (`wallet_id`, `created_at` DESC),
    INDEX `wallet_txn_user_created_idx` (`user_id`, `created_at` DESC),
    INDEX `wallet_txn_tx_type_idx` (`tx_type`),
    CONSTRAINT `fk_wallet_txn_wallet` FOREIGN KEY (`wallet_id`) REFERENCES `wallets` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_wallet_txn_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
'''


class Migration(migrations.Migration):
    '''Create wallet and wallet_transaction tables (idempotent).'''

    dependencies = [
        ('payments', '0003_admin_fee_tracking'),
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='Wallet',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('balance', models.DecimalField(decimal_places=2, default=0, max_digits=14, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Saldo')),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('updated_at', models.DateTimeField(auto_now=True)),
                        ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='wallet', to='accounts.User', verbose_name='Pengguna')),
                    ],
                    options={
                        'db_table': 'wallets',
                        'verbose_name': 'Dompet',
                        'verbose_name_plural': 'Dompet',
                    },
                ),
                migrations.CreateModel(
                    name='WalletTransaction',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('tx_type', models.CharField(choices=[('topup', 'Top Up'), ('payment', 'Pembayaran'), ('refund', 'Refund'), ('withdrawal', 'Penarikan'), ('bonus', 'Bonus'), ('adjustment', 'Penyesuaian')], max_length=20, verbose_name='Tipe Transaksi')),
                        ('amount', models.DecimalField(decimal_places=2, max_digits=14, verbose_name='Jumlah')),
                        ('balance_before', models.DecimalField(decimal_places=2, max_digits=14, verbose_name='Saldo Sebelum')),
                        ('balance_after', models.DecimalField(decimal_places=2, max_digits=14, verbose_name='Saldo Sesudah')),
                        ('description', models.CharField(blank=True, max_length=255, null=True, verbose_name='Deskripsi')),
                        ('reference_type', models.CharField(blank=True, help_text='order, midtrans, withdrawal', max_length=50, null=True, verbose_name='Tipe Referensi')),
                        ('reference_id', models.CharField(blank=True, max_length=100, null=True, verbose_name='ID Referensi')),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='wallet_transactions', to='accounts.User')),
                        ('wallet', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='payments.Wallet', verbose_name='Dompet')),
                    ],
                    options={
                        'db_table': 'wallet_transactions',
                        'verbose_name': 'Transaksi Dompet',
                        'verbose_name_plural': 'Transaksi Dompet',
                        'ordering': ['-created_at'],
                        'indexes': [models.Index(fields=['wallet', '-created_at']), models.Index(fields=['user', '-created_at']), models.Index(fields=['tx_type'])],
                    },
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql=CREATE_WALLETS_SQL,
                    reverse_sql='DROP TABLE IF EXISTS `wallets`;'
                ),
                migrations.RunSQL(
                    sql=CREATE_WALLET_TXNS_SQL,
                    reverse_sql='DROP TABLE IF EXISTS `wallet_transactions`;'
                ),
            ],
        ),
    ]
