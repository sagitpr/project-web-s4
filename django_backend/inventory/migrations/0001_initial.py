"""Initial migration for inventory management app."""
from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ('accounts', '0001_initial'),
        ('stores', '0001_initial'),
        ('products', '0001_initial'),
    ]
    operations = [
        migrations.CreateModel(
            name='MasterProduct',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('barcode', models.CharField(db_index=True, help_text='13-digit EAN-13 barcode number', max_length=13, unique=True, verbose_name='Barcode (EAN-13)')),
                ('product_name', models.CharField(max_length=200, verbose_name='Nama Produk')),
                ('brand', models.CharField(blank=True, max_length=100, verbose_name='Merek')),
                ('category', models.CharField(db_index=True, help_text='Seperti: Makanan, Minuman, Sembako, Produk Rumah Tangga', max_length=100, verbose_name='Kategori')),
                ('subcategory', models.CharField(blank=True, max_length=100, verbose_name='Subkategori')),
                ('unit', models.CharField(choices=[('pcs', 'Piece'), ('kg', 'Kilogram'), ('g', 'Gram'), ('liter', 'Liter'), ('ml', 'Mililiter'), ('pack', 'Pack'), ('dus', 'Dus (Karton)'), ('karung', 'Karung'), ('botol', 'Botol'), ('kaleng', 'Kaleng'), ('sachet', 'Sachet'), ('box', 'Box')], default='pcs', max_length=20, verbose_name='Satuan')),
                ('weight_value', models.DecimalField(blank=True, decimal_places=2, help_text='Berat bersih dalam gram atau volume dalam ml', max_digits=10, null=True, verbose_name='Berat/Volume')),
                ('weight_unit', models.CharField(blank=True, help_text='g, kg, ml, liter', max_length=10, verbose_name='Satuan Berat')),
                ('image_url', models.URLField(blank=True, help_text='Product image URL from barcode database', verbose_name='URL Gambar')),
                ('manufacturer', models.CharField(blank=True, max_length=200, verbose_name='Produsen')),
                ('bpom_number', models.CharField(blank=True, help_text='BPOM/POM registration number for Indonesian products', max_length=30, verbose_name='Nomor BPOM')),
                ('is_active', models.BooleanField(default=True, verbose_name='Aktif')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Master Produk',
                'verbose_name_plural': 'Master Produk',
                'db_table': 'inventory_master_product',
                'ordering': ['product_name'],
            },
        ),
        migrations.AddIndex(
            model_name='masterproduct',
            index=models.Index(fields=['barcode'], name='inventory_m_barcode_a41bde_idx'),
        ),
        migrations.AddIndex(
            model_name='masterproduct',
            index=models.Index(fields=['product_name'], name='inventory_m_product_302c3d_idx'),
        ),
        migrations.AddIndex(
            model_name='masterproduct',
            index=models.Index(fields=['category'], name='inventory_m_category_0f3daf_idx'),
        ),
        migrations.AddIndex(
            model_name='masterproduct',
            index=models.Index(fields=['brand'], name='inventory_m_brand_0f3daf_idx'),
        ),
        migrations.CreateModel(
            name='ProductBatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('batch_number', models.CharField(help_text='Batch number from manufacturer', max_length=100, verbose_name='Nomor Batch/Lot')),
                ('production_date', models.DateField(verbose_name='Tanggal Produksi')),
                ('expiry_date', models.DateField(verbose_name='Tanggal Kadaluwarsa')),
                ('initial_quantity', models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Jumlah Awal')),
                ('current_quantity', models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Jumlah Tersisa')),
                ('unit', models.CharField(default='pcs', max_length=20, verbose_name='Satuan')),
                ('purchase_price', models.DecimalField(blank=True, decimal_places=2, help_text='Purchase price per unit', max_digits=12, null=True, verbose_name='Harga Beli')),
                ('shelf_life_days', models.IntegerField(editable=False, verbose_name='Masa Simpan (hari)')),
                ('shelf_life_remaining_pct', models.DecimalField(decimal_places=2, default=100.0, editable=False, max_digits=5, verbose_name='Sisa Masa Simpan (%)')),
                ('status', models.CharField(choices=[('fresh', 'Fresh'), ('expiring_soon', 'Expiring Soon'), ('expired', 'Expired'), ('disposed', 'Disposed')], db_index=True, default='fresh', max_length=20, verbose_name='Status')),
                ('notes', models.TextField(blank=True, verbose_name='Catatan')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('master_product', models.ForeignKey(on_delete=models.CASCADE, related_name='batches', to='inventory.masterproduct', verbose_name='Master Produk')),
                ('product', models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name='batches', to='products.product', verbose_name='Product Listing')),
                ('store', models.ForeignKey(on_delete=models.CASCADE, related_name='product_batches', to='stores.store', verbose_name='Toko')),
            ],
            options={
                'verbose_name': 'Batch Produk',
                'verbose_name_plural': 'Batch Produk',
                'db_table': 'inventory_product_batch',
                'ordering': ['expiry_date', 'batch_number'],
            },
        ),
        migrations.AddIndex(
            model_name='productbatch',
            index=models.Index(fields=['store', 'status'], name='inventory_p_store_s_a1b2c3_idx'),
        ),
        migrations.AddIndex(
            model_name='productbatch',
            index=models.Index(fields=['expiry_date'], name='inventory_p_expiry_d4e5f6_idx'),
        ),
        migrations.AddIndex(
            model_name='productbatch',
            index=models.Index(fields=['batch_number'], name='inventory_p_batch_n_g7h8i9_idx'),
        ),
        migrations.AddIndex(
            model_name='productbatch',
            index=models.Index(fields=['master_product', 'expiry_date'], name='inventory_p_master__j0k1l2_idx'),
        ),
        migrations.CreateModel(
            name='ExpiryNotification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notification_type', models.CharField(choices=[('expiring_soon', 'Akan Kadaluwarsa'), ('expired', 'Kadaluwarsa'), ('disposal', 'Buang Stok')], max_length=20, verbose_name='Tipe Notifikasi')),
                ('days_until_expiry', models.IntegerField(verbose_name='Hari Menuju Kadaluwarsa')),
                ('sent_at', models.DateTimeField(auto_now_add=True)),
                ('batch', models.ForeignKey(on_delete=models.CASCADE, related_name='expiry_notifications', to='inventory.productbatch', verbose_name='Batch')),
                ('store', models.ForeignKey(on_delete=models.CASCADE, related_name='expiry_notifications', to='stores.store', verbose_name='Toko')),
            ],
            options={
                'verbose_name': 'Notifikasi Kadaluwarsa',
                'verbose_name_plural': 'Notifikasi Kadaluwarsa',
                'db_table': 'inventory_expiry_notifications',
            },
        ),
        migrations.AddIndex(
            model_name='expirynotification',
            index=models.Index(fields=['store', 'notification_type'], name='inventory_e_store_n_m3n4o5_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='expirynotification',
            unique_together={('batch', 'notification_type')},
        ),
        migrations.CreateModel(
            name='StockAlert',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('min_stock', models.DecimalField(decimal_places=2, default=10, max_digits=12, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Stok Minimum')),
                ('max_stock', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Stok Maksimum')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('master_product', models.ForeignKey(on_delete=models.CASCADE, related_name='stock_alerts', to='inventory.masterproduct', verbose_name='Master Produk')),
                ('store', models.ForeignKey(on_delete=models.CASCADE, related_name='stock_alerts', to='stores.store', verbose_name='Toko')),
            ],
            options={
                'verbose_name': 'Alert Stok',
                'verbose_name_plural': 'Alert Stok',
                'db_table': 'inventory_stock_alerts',
            },
        ),
        migrations.AlterUniqueTogether(
            name='stockalert',
            unique_together={('store', 'master_product')},
        ),
        migrations.CreateModel(
            name='InventoryStock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('transaction_type', models.CharField(choices=[('stock_in', 'Stock In'), ('stock_out', 'Stock Out'), ('adjustment', 'Adjustment'), ('disposal', 'Disposal'), ('return', 'Return'), ('transfer', 'Transfer')], max_length=20, verbose_name='Tipe Transaksi')),
                ('quantity', models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Jumlah')),
                ('quantity_before', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Stok Sebelum')),
                ('quantity_after', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Stok Sesudah')),
                ('reference_type', models.CharField(blank=True, help_text='e.g., order_id, purchase_order_id', max_length=50, verbose_name='Tipe Referensi')),
                ('reference_id', models.CharField(blank=True, max_length=50, verbose_name='ID Referensi')),
                ('notes', models.TextField(blank=True, verbose_name='Catatan')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('batch', models.ForeignKey(help_text='FEFO: pick the batch with nearest expiry', on_delete=models.CASCADE, related_name='stock_transactions', to='inventory.productbatch', verbose_name='Batch')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, to='accounts.user', verbose_name='Dibuat Oleh')),
                ('master_product', models.ForeignKey(on_delete=models.CASCADE, related_name='stock_transactions', to='inventory.masterproduct', verbose_name='Master Produk')),
                ('product', models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name='stock_transactions', to='products.product', verbose_name='Product Listing')),
                ('store', models.ForeignKey(on_delete=models.CASCADE, related_name='inventory_transactions', to='stores.store', verbose_name='Toko')),
            ],
            options={
                'verbose_name': 'Transaksi Stok',
                'verbose_name_plural': 'Transaksi Stok',
                'db_table': 'inventory_stock_transactions',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='inventorystock',
            index=models.Index(fields=['store', 'transaction_type'], name='inventory_s_store_i_d3b9b5_idx'),
        ),
        migrations.AddIndex(
            model_name='inventorystock',
            index=models.Index(fields=['batch'], name='inventory_s_batch_i_b1f2a3_idx'),
        ),
        migrations.AddIndex(
            model_name='inventorystock',
            index=models.Index(fields=['created_at'], name='inventory_s_created_c4d5e6_idx'),
        ),
        migrations.AddIndex(
            model_name='inventorystock',
            index=models.Index(fields=['master_product'], name='inventory_s_master__e7f8g9_idx'),
        ),
    ]
