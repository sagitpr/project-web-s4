from django.contrib import admin
from .models import Refund, RefundTimelineEvent


class RefundTimelineInline(admin.TabularInline):
    model = RefundTimelineEvent
    extra = 0
    readonly_fields = ('event_type', 'description', 'created_by', 'created_by_role', 'created_at')
    can_delete = False
    ordering = ('-created_at',)


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ('refund_number', 'order', 'user', 'store', 'amount_requested',
                    'amount_approved', 'refund_status', 'is_escalated', 'created_at')
    list_filter = ('refund_status', 'reason', 'is_escalated', 'created_at')
    search_fields = ('refund_number', 'order__order_number', 'user__email', 'store__store_name')
    readonly_fields = ('refund_number', 'created_at', 'updated_at', 'resolved_at')
    inlines = [RefundTimelineInline]
    fieldsets = (
        ('Informasi Refund', {
            'fields': ('refund_number', 'order', 'user', 'store')
        }),
        ('Detail', {
            'fields': ('reason', 'reason_text', 'amount_requested', 'amount_approved',
                       'refund_status', 'resolution', 'is_escalated')
        }),
        ('Bukti & Catatan', {
            'fields': ('evidence_images', 'evidence_description', 'refund_items',
                       'buyer_notes', 'seller_notes', 'admin_notes')
        }),
        ('Waktu', {
            'fields': ('created_at', 'updated_at', 'resolved_at')
        }),
    )


@admin.register(RefundTimelineEvent)
class RefundTimelineEventAdmin(admin.ModelAdmin):
    list_display = ('refund', 'event_type', 'created_by', 'created_at')
    list_filter = ('event_type', 'created_at')
    search_fields = ('refund__refund_number', 'description')
    readonly_fields = ('created_at',)
