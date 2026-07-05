'''Migration: Create Wallet and WalletTransaction tables.

Uses plain CreateModel (works on all database engines including SQLite).
For MySQL production, the tables are created by Django's ORM automatically.
'''
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):
    '''Create wallet and wallet_transaction tables.'''

    dependencies = [
        ('payments', '0003_admin_fee_tracking'),
        ('accounts', '0001_initial'),
    ]

    operations = [
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
                'indexes': [models.Index(fields=['wallet', '-created_at'], name='wallet_txn_wallet_created_idx'), models.Index(fields=['user', '-created_at'], name='wallet_txn_user_created_idx'), models.Index(fields=['tx_type'], name='wallet_txn_tx_type_idx')],
            },
        ),
    ]
