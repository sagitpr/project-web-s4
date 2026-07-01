"""
Django Admin configuration for inventory management.
"""

from django.contrib import admin
from .models import MasterProduct, ProductBatch, InventoryStock, ExpiryNotification, StockAlert


@admin.register(MasterProduct)
class MasterProductAdmin(admin.ModelAdmin):
    list_display = ['barcode', 'product_name', 'brand', 'category', 'unit', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['barcode', 'product_name', 'brand', 'manufacturer']
    list_editable = ['is_active']
    ordering = ['product_name']


class InventoryStockInline(admin.TabularInline):
    model = InventoryStock
    extra = 0
    fields = ['transaction_type', 'quantity', 'quantity_before', 'quantity_after', 'created_at']
    readonly_fields = ['created_at']
    can_delete = False
    max_num = 10


@admin.register(ProductBatch)
class ProductBatchAdmin(admin.ModelAdmin):
    list_display = [
        'batch_number', 'master_product', 'store', 'current_quantity',
        'unit', 'production_date', 'expiry_date', 'shelf_life_days',
        'shelf_life_remaining_pct', 'status',
    ]
    list_filter = ['status', 'store', 'unit']
    search_fields = ['batch_number', 'master_product__product_name']
    readonly_fields = ['shelf_life_days', 'shelf_life_remaining_pct', 'status']
    inlines = [InventoryStockInline]


@admin.register(InventoryStock)
class InventoryStockAdmin(admin.ModelAdmin):
    list_display = [
        'store', 'master_product', 'batch', 'transaction_type',
        'quantity', 'quantity_before', 'quantity_after', 'created_at',
    ]
    list_filter = ['transaction_type', 'store']
    search_fields = ['master_product__product_name', 'batch__batch_number']
    readonly_fields = ['created_at']


@admin.register(ExpiryNotification)
class ExpiryNotificationAdmin(admin.ModelAdmin):
    list_display = ['batch', 'store', 'notification_type', 'days_until_expiry', 'sent_at']
    list_filter = ['notification_type', 'store']
    readonly_fields = ['sent_at']


@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    list_display = ['store', 'master_product', 'min_stock', 'max_stock', 'is_active']
    list_filter = ['is_active', 'store']
    search_fields = ['master_product__product_name']
    list_editable = ['min_stock', 'is_active']
