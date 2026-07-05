# Generated manually — adds admin_fee column back
# Migration 0008 removed it but the current model still uses admin_fee

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0008_admin_fee_dual'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='admin_fee',
            field=models.DecimalField(decimal_places=2, default=Decimal('1000.00'), max_digits=10, verbose_name='Biaya Admin (Seller)'),
        ),
    ]
