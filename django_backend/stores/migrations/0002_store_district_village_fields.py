"""Add district, village, and region code fields to Store model."""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('stores', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='store',
            name='district',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Kecamatan'),
        ),
        migrations.AddField(
            model_name='store',
            name='district_code',
            field=models.CharField(blank=True, max_length=6, null=True, verbose_name='Kode Kecamatan'),
        ),
        migrations.AddField(
            model_name='store',
            name='village',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Desa/Kelurahan'),
        ),
        migrations.AddField(
            model_name='store',
            name='village_code',
            field=models.CharField(blank=True, max_length=10, null=True, verbose_name='Kode Desa/Kelurahan'),
        ),
        migrations.AddField(
            model_name='store',
            name='city_code',
            field=models.CharField(blank=True, max_length=4, null=True, verbose_name='Kode Kota/Kabupaten'),
        ),
        migrations.AddField(
            model_name='store',
            name='province_code',
            field=models.CharField(blank=True, max_length=2, null=True, verbose_name='Kode Provinsi'),
        ),
    ]
