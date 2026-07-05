"""
Migration: Add reserved_stock field to Product model.

This field tracks stock that has been reserved by buyers 
but not yet scanned for packing.
"""

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):
    """Add reserved_stock field to Product model."""

    dependencies = [
        ('products', '0005_recentlyviewed'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='reserved_stock',
            field=models.IntegerField(
                default=0,
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name='Stok Dipesan',
                help_text='Jumlah yang sudah dipesan buyer tapi belum di-scan untuk packing',
            ),
        ),
    ]
