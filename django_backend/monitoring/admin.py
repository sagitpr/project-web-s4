"""
Monitoring admin configuration for Warungio Marketplace.
"""
from django.contrib import admin
from .models import SystemHealth, PerformanceMetric, UptimeRecord, ErrorLog, ScheduledTask


@admin.register(SystemHealth)
class SystemHealthAdmin(admin.ModelAdmin):
    list_display = ['service_name', 'status', 'response_time_ms', 'error_rate', 'checked_at']
    list_filter = ['service_name', 'status']
    search_fields = ['service_name']
    readonly_fields = ['checked_at']
    date_hierarchy = 'checked_at'


@admin.register(PerformanceMetric)
class PerformanceMetricAdmin(admin.ModelAdmin):
    list_display = ['metric_type', 'value', 'unit', 'recorded_at']
    list_filter = ['metric_type']
    search_fields = ['metric_type']
    readonly_fields = ['recorded_at']


@admin.register(UptimeRecord)
class UptimeRecordAdmin(admin.ModelAdmin):
    list_display = ['date', 'uptime_percent', 'total_checks', 'failed_checks', 'avg_response_time_ms']
    list_filter = ['date']
    date_hierarchy = 'date'
    readonly_fields = ['created_at']


@admin.register(ErrorLog)
class ErrorLogAdmin(admin.ModelAdmin):
    list_display = ['service', 'severity', 'message_short', 'endpoint', 'status_code', 'resolved', 'created_at']
    list_filter = ['severity', 'service', 'resolved']
    search_fields = ['message', 'service', 'endpoint']
    readonly_fields = ['created_at']
    actions = ['mark_resolved']
    date_hierarchy = 'created_at'

    def message_short(self, obj):
        return obj.message[:80] + '...' if len(obj.message) > 80 else obj.message
    message_short.short_description = 'Message'

    def mark_resolved(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(resolved=True, resolved_at=timezone.now(), resolved_by=request.user)
        self.message_user(request, f'{updated} errors marked as resolved.')
    mark_resolved.short_description = 'Mark as resolved'


@admin.register(ScheduledTask)
class ScheduledTaskAdmin(admin.ModelAdmin):
    list_display = ['task_name', 'task_type', 'status', 'started_at', 'completed_at', 'duration_ms']
    list_filter = ['status', 'task_type']
    search_fields = ['task_name']
    readonly_fields = ['created_at']
