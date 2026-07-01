"""Add AI Smart Inventory Scanning models."""
from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):
    dependencies = [
        ('inventory', '0001_initial'),
    ]
    operations = [
        migrations.CreateModel(
            name='SmartScanSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('scan_mode', models.CharField(choices=[('single', 'Single Product'), ('multi', 'Multi Product'), ('bulk', 'Bulk / Shelf Scan')], default='multi', max_length=20, verbose_name='Mode Scan')),
                ('status', models.CharField(choices=[('scanning', 'Scanning'), ('review', 'Awaiting Review'), ('confirmed', 'Confirmed'), ('saved', 'Saved to Inventory'), ('cancelled', 'Cancelled')], db_index=True, default='scanning', max_length=20, verbose_name='Status')),
                ('frame_count', models.IntegerField(default=0, verbose_name='Jumlah Frame')),
                ('total_items_detected', models.IntegerField(default=0, verbose_name='Item Terdeteksi')),
                ('total_items_confirmed', models.IntegerField(default=0, verbose_name='Item Dikonfirmasi')),
                ('total_batches_created', models.IntegerField(default=0, verbose_name='Batch Dibuat')),
                ('started_at', models.DateTimeField(auto_now_add=True, verbose_name='Mulai')),
                ('completed_at', models.DateTimeField(blank=True, null=True, verbose_name='Selesai')),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('store', models.ForeignKey(on_delete=models.CASCADE, related_name='ai_scan_sessions', to='stores.store', verbose_name='Toko')),
                ('user', models.ForeignKey(on_delete=models.CASCADE, related_name='ai_scan_sessions', to='accounts.user', verbose_name='Pengguna')),
            ],
            options={
                'verbose_name': 'Sesi Scan AI',
                'verbose_name_plural': 'Sesi Scan AI',
                'db_table': 'ai_scan_sessions',
                'ordering': ['-started_at'],
            },
        ),
        migrations.AddIndex(
            model_name='smartscansession',
            index=models.Index(fields=['store', 'status'], name='ai_scan_sessions_store_status_idx'),
        ),
        migrations.AddIndex(
            model_name='smartscansession',
            index=models.Index(fields=['user'], name='ai_scan_sessions_user_idx'),
        ),
        migrations.AddIndex(
            model_name='smartscansession',
            index=models.Index(fields=['started_at'], name='ai_scan_sessions_started_at_idx'),
        ),
        migrations.CreateModel(
            name='DetectedItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('detection_method', models.CharField(choices=[('object_detection', 'Object Detection'), ('barcode', 'Barcode Recognition'), ('ocr', 'OCR Text Recognition'), ('manual', 'Manual Entry'), ('combined', 'Combined (AI Aggregate)')], max_length=30, verbose_name='Metode Deteksi')),
                ('confidence_score', models.DecimalField(decimal_places=2, help_text='Overall AI confidence (0.00 - 1.00)', max_digits=5, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(1)], verbose_name='Skor Keyakinan')),
                ('detected_count', models.IntegerField(default=1, help_text='Number of identical items found (e.g., 12 bottles)', validators=[django.core.validators.MinValueValidator(1)], verbose_name='Jumlah Terdeteksi')),
                ('confirmed_count', models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Jumlah Dikonfirmasi')),
                ('unit', models.CharField(default='pcs', max_length=20, verbose_name='Satuan')),
                ('detected_barcode', models.CharField(blank=True, help_text='Barcode value detected via camera', max_length=20, verbose_name='Barcode Terdeteksi')),
                ('barcode_confidence', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, verbose_name='Confidence Barcode')),
                ('detected_batch_number', models.CharField(blank=True, max_length=100, verbose_name='Batch Terdeteksi (OCR)')),
                ('detected_expiry_date', models.DateField(blank=True, null=True, verbose_name='Expiry Terdeteksi (OCR)')),
                ('detected_product_name', models.CharField(blank=True, max_length=200, verbose_name='Nama Produk Terdeteksi (OCR)')),
                ('detected_brand', models.CharField(blank=True, max_length=100, verbose_name='Merek Terdeteksi (OCR)')),
                ('ocr_confidence', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, verbose_name='Confidence OCR')),
                ('bounding_box', models.JSONField(blank=True, help_text='Bounding box coordinates: {x, y, width, height}', null=True, verbose_name='Bounding Box')),
                ('detection_features', models.JSONField(blank=True, help_text='Visual features: color, shape, detected labels, stacked/hanging flags', null=True, verbose_name='Fitur Deteksi')),
                ('frame_number', models.IntegerField(default=0, help_text='Camera frame number where this item was detected', verbose_name='Frame Number')),
                ('confirmation_status', models.CharField(choices=[('pending', 'Pending Review'), ('accepted', 'Accepted by User'), ('corrected', 'Corrected by User'), ('rejected', 'Rejected by User')], default='pending', max_length=20, verbose_name='Status Konfirmasi')),
                ('user_notes', models.TextField(blank=True, verbose_name='Catatan Pengguna')),
                ('detected_at', models.DateTimeField(auto_now_add=True)),
                ('confirmed_at', models.DateTimeField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_batch', models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name='ai_scan_items', to='inventory.productbatch', verbose_name='Batch Dibuat')),
                ('master_product', models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name='ai_detections', to='inventory.masterproduct', verbose_name='Master Produk')),
                ('session', models.ForeignKey(on_delete=models.CASCADE, related_name='detected_items', to='inventory.smartscansession', verbose_name='Sesi Scan')),
                ('store', models.ForeignKey(on_delete=models.CASCADE, related_name='ai_detected_items', to='stores.store', verbose_name='Toko')),
            ],
            options={
                'verbose_name': 'Item Terdeteksi AI',
                'verbose_name_plural': 'Item Terdeteksi AI',
                'db_table': 'ai_detected_items',
                'ordering': ['-detected_at'],
            },
        ),
        migrations.AddIndex(
            model_name='detecteditem',
            index=models.Index(fields=['session', 'confirmation_status'], name='ai_detected_items_session_status_idx'),
        ),
        migrations.AddIndex(
            model_name='detecteditem',
            index=models.Index(fields=['master_product'], name='ai_detected_items_master_product_idx'),
        ),
        migrations.AddIndex(
            model_name='detecteditem',
            index=models.Index(fields=['detection_method'], name='ai_detected_items_method_idx'),
        ),
        migrations.AddIndex(
            model_name='detecteditem',
            index=models.Index(fields=['detected_barcode'], name='ai_detected_items_barcode_idx'),
        ),
    ]
