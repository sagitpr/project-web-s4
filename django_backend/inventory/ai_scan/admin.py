"""
Django Admin configuration for AI Smart Inventory Scanning.
"""

from django.contrib import admin
from inventory.models import SmartScanSession, DetectedItem


class DetectedItemInline(admin.TabularInline):
    model = DetectedItem
    extra = 0
    fields = [
        'detection_method', 'confidence_score', 'master_product',
        'detected_count', 'confirmed_count',
        'detected_barcode', 'detected_batch_number',
        'detected_expiry_date', 'confirmation_status',
        'created_batch',
    ]
    readonly_fields = ['detected_at']
    can_delete = False
    max_num = 20


@admin.register(SmartScanSession)
class SmartScanSessionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'store', 'user', 'scan_mode', 'status',
        'total_items_detected', 'total_items_confirmed',
        'total_batches_created', 'started_at',
    ]
    list_filter = ['status', 'scan_mode', 'store']
    search_fields = ['store__store_name', 'user__email']
    readonly_fields = [
        'frame_count', 'total_items_detected', 'total_items_confirmed',
        'total_batches_created', 'started_at', 'completed_at', 'updated_at',
    ]
    inlines = [DetectedItemInline]


@admin.register(DetectedItem)
class DetectedItemAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'session', 'master_product', 'detection_method',
        'confidence_score', 'detected_count', 'confirmed_count',
        'detected_barcode', 'confirmation_status',
    ]
    list_filter = ['detection_method', 'confirmation_status', 'store']
    search_fields = [
        'detected_barcode', 'detected_product_name',
        'master_product__product_name', 'detected_batch_number',
    ]
    readonly_fields = ['detected_at', 'confirmed_at']
