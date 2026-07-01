"""
Supplier admin configuration for Warungio Marketplace.
"""
from django.contrib import admin
from .models import (
    Supplier, SupplierCategory, SupplierProduct, SupplierOrder,
    SupplierOrderItem, SupplierReview, SupplierContract, SupplierPayment
)


@admin.register(SupplierCategory)
class SupplierCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'sort_order', 'supplier_count']
    list_filter = ['is_active']
    search_fields = ['name']
    ordering = ['sort_order']

    def supplier_count(self, obj):
        return obj.suppliers.filter(is_active=True).count()
    supplier_count.short_description = 'Jumlah Supplier'


class SupplierProductInline(admin.TabularInline):
    model = SupplierProduct
    extra = 1
    fields = ['product_name', 'sku', 'unit_price', 'stock_available', 'is_available']


class SupplierReviewInline(admin.TabularInline):
    model = SupplierReview
    extra = 0
    readonly_fields = ['created_at']
    can_delete = False


class SupplierContractInline(admin.TabularInline):
    model = SupplierContract
    extra = 0
    fields = ['contract_number', 'contract_type', 'status', 'start_date', 'end_date']
    readonly_fields = ['contract_number']


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = [
        'supplier_name', 'category_name', 'city', 'status',
        'verification_level', 'rating_avg', 'on_time_delivery_rate',
        'total_products_supplied', 'is_featured',
    ]
    list_filter = ['status', 'verification_level', 'city', 'is_featured', 'is_active']
    search_fields = ['supplier_name', 'email', 'phone', 'contact_person']
    prepopulated_fields = {'slug': ('supplier_name',)}
    inlines = [SupplierProductInline, SupplierReviewInline, SupplierContractInline]
    fieldsets = [
        ('Identitas', {'fields': ['supplier_name', 'slug', 'category', 'description']}),
        ('Kontak', {'fields': ['contact_person', 'email', 'phone', 'whatsapp', 'website']}),
        ('Alamat', {'fields': ['address', 'city', 'province', 'postal_code', 'latitude', 'longitude']}),
        ('Bisnis', {'fields': ['npwp', 'business_license', 'bank_name', 'bank_account', 'bank_owner']}),
        ('Pembayaran', {'fields': ['payment_terms', 'min_order', 'shipping_cost_borne']}),
        ('Status', {'fields': ['status', 'verification_level', 'verified_at', 'verified_by', 'is_active', 'is_featured']}),
        ('Rating', {'fields': ['rating_avg', 'rating_count', 'quality_score', 'on_time_delivery_rate']}),
        ('Operasional', {'fields': ['lead_time_days', 'delivery_coverage', 'product_categories']}),
        ('Lainnya', {'fields': ['logo', 'banner', 'documents', 'notes', 'tags']}),
    ]
    readonly_fields = ['slug', 'rating_avg', 'rating_count', 'created_at', 'updated_at']
    actions = ['verify_suppliers', 'activate_suppliers', 'suspend_suppliers']

    def verify_suppliers(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(
            verification_level='verified', status='active',
            verified_at=timezone.now(), verified_by=request.user
        )
        self.message_user(request, f'{updated} supplier berhasil diverifikasi.')
    verify_suppliers.short_description = 'Verifikasi supplier terpilih'

    def activate_suppliers(self, request, queryset):
        updated = queryset.update(status='active')
        self.message_user(request, f'{updated} supplier diaktifkan.')
    activate_suppliers.short_description = 'Aktifkan supplier terpilih'

    def suspend_suppliers(self, request, queryset):
        updated = queryset.update(status='suspended')
        self.message_user(request, f'{updated} supplier dinonaktifkan.')
    suspend_suppliers.short_description = 'Nonaktifkan supplier terpilih'

    def category_name(self, obj):
        return obj.category.name if obj.category else '-'
    category_name.short_description = 'Kategori'


@admin.register(SupplierProduct)
class SupplierProductAdmin(admin.ModelAdmin):
    list_display = ['product_name', 'supplier', 'unit_price', 'stock_available', 'is_available', 'is_active']
    list_filter = ['is_available', 'is_active', 'category']
    search_fields = ['product_name', 'sku', 'supplier__supplier_name']
    list_select_related = ['supplier']


class SupplierOrderItemInline(admin.TabularInline):
    model = SupplierOrderItem
    extra = 1
    fields = ['product_name', 'sku', 'qty', 'unit', 'unit_price', 'subtotal']
    readonly_fields = ['subtotal']


@admin.register(SupplierOrder)
class SupplierOrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'supplier', 'store', 'status', 'payment_status', 'total_amount', 'ordered_at']
    list_filter = ['status', 'payment_status']
    search_fields = ['order_number', 'supplier__supplier_name', 'store__store_name']
    inlines = [SupplierOrderItemInline]
    readonly_fields = ['order_number', 'subtotal', 'total_amount', 'ordered_at']
    date_hierarchy = 'ordered_at'


@admin.register(SupplierReview)
class SupplierReviewAdmin(admin.ModelAdmin):
    list_display = ['supplier', 'user', 'rating', 'delivery_timeliness', 'product_quality', 'created_at']
    list_filter = ['rating']
    search_fields = ['supplier__supplier_name', 'user__email']
    readonly_fields = ['created_at']


@admin.register(SupplierContract)
class SupplierContractAdmin(admin.ModelAdmin):
    list_display = ['contract_number', 'supplier', 'contract_type', 'status', 'start_date', 'end_date']
    list_filter = ['status', 'contract_type']
    search_fields = ['contract_number', 'supplier__supplier_name']
    readonly_fields = ['contract_number', 'created_at']


@admin.register(SupplierPayment)
class SupplierPaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_number', 'supplier', 'amount', 'payment_method', 'status', 'payment_date']
    list_filter = ['status', 'payment_method']
    search_fields = ['payment_number', 'supplier__supplier_name']
    readonly_fields = ['payment_number', 'created_at']
