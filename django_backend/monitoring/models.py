"""
Server Monitoring models for Warungio Marketplace.
System health checks, performance metrics, uptime tracking.
"""

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class SystemHealth(models.Model):
    """System health check records."""
    STATUS_CHOICES = [
        ('healthy', 'Healthy'),
        ('degraded', 'Degraded'),
        ('down', 'Down'),
        ('maintenance', 'Maintenance'),
    ]

    service_name = models.CharField(max_length=100, verbose_name='Nama Service')
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='healthy',
        verbose_name='Status'
    )
    response_time_ms = models.IntegerField(default=0, verbose_name='Response Time (ms)')
    error_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name='Error Rate (%)',
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    details = models.JSONField(default=dict, blank=True, verbose_name='Detail')
    checked_at = models.DateTimeField(auto_now_add=True, verbose_name='Waktu Cek')

    class Meta:
        db_table = 'system_health'
        verbose_name = 'Kesehatan Sistem'
        verbose_name_plural = 'Kesehatan Sistem'
        indexes = [
            models.Index(fields=['service_name', '-checked_at']),
            models.Index(fields=['status']),
            models.Index(fields=['checked_at']),
        ]
        ordering = ['-checked_at']

    def __str__(self):
        return f'{self.service_name}: {self.status} ({self.response_time_ms}ms)'


class PerformanceMetric(models.Model):
    """Performance metrics for monitoring."""
    METRIC_TYPES = [
        ('cpu', 'CPU Usage'),
        ('memory', 'Memory Usage'),
        ('disk', 'Disk Usage'),
        ('db_connections', 'DB Connections'),
        ('request_count', 'Request Count'),
        ('active_users', 'Active Users'),
        ('api_latency', 'API Latency'),
        ('queue_size', 'Queue Size'),
        ('cache_hit_rate', 'Cache Hit Rate'),
        ('websocket_connections', 'WebSocket Connections'),
    ]

    metric_type = models.CharField(max_length=30, choices=METRIC_TYPES, verbose_name='Tipe Metrik')
    value = models.FloatField(verbose_name='Nilai')
    unit = models.CharField(max_length=30, blank=True, null=True, verbose_name='Satuan')
    tags = models.JSONField(default=dict, blank=True, verbose_name='Tags')
    recorded_at = models.DateTimeField(auto_now_add=True, verbose_name='Waktu Rekam')

    class Meta:
        db_table = 'performance_metrics'
        verbose_name = 'Metrik Performa'
        verbose_name_plural = 'Metrik Performa'
        indexes = [
            models.Index(fields=['metric_type', '-recorded_at']),
            models.Index(fields=['recorded_at']),
        ]
        ordering = ['-recorded_at']

    def __str__(self):
        return f'{self.get_metric_type_display()}: {self.value}{self.unit or ""}'


class UptimeRecord(models.Model):
    """Daily uptime percentage tracking."""
    date = models.DateField(unique=True, verbose_name='Tanggal')
    uptime_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=100.00,
        verbose_name='Uptime (%)',
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    total_checks = models.IntegerField(default=0, verbose_name='Total Cek')
    failed_checks = models.IntegerField(default=0, verbose_name='Gagal')
    avg_response_time_ms = models.IntegerField(default=0, verbose_name='Rata-rata Response (ms)')
    downtime_seconds = models.IntegerField(default=0, verbose_name='Downtime (detik)')
    notes = models.TextField(blank=True, null=True, verbose_name='Catatan')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'uptime_records'
        verbose_name = 'Uptime Record'
        verbose_name_plural = 'Uptime Records'
        ordering = ['-date']

    def __str__(self):
        return f'{self.date}: {self.uptime_percent}% uptime'


class ErrorLog(models.Model):
    """Application error logs for monitoring."""
    SEVERITY_CHOICES = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    ]

    service = models.CharField(max_length=100, verbose_name='Service')
    severity = models.CharField(
        max_length=20, choices=SEVERITY_CHOICES, default='error',
        verbose_name='Severity'
    )
    message = models.TextField(verbose_name='Pesan')
    stack_trace = models.TextField(blank=True, null=True, verbose_name='Stack Trace')
    endpoint = models.CharField(max_length=500, blank=True, null=True, verbose_name='Endpoint')
    method = models.CharField(max_length=10, blank=True, null=True, verbose_name='Method')
    status_code = models.IntegerField(null=True, blank=True, verbose_name='Status Code')
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name='IP')
    user_agent = models.TextField(blank=True, null=True, verbose_name='User Agent')
    user_id = models.IntegerField(null=True, blank=True, verbose_name='User ID')
    metadata = models.JSONField(default=dict, blank=True, verbose_name='Metadata')
    resolved = models.BooleanField(default=False, verbose_name='Resolved')
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name='Resolved At')
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='resolved_errors'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'error_logs'
        verbose_name = 'Error Log'
        verbose_name_plural = 'Error Logs'
        indexes = [
            models.Index(fields=['severity']),
            models.Index(fields=['service', '-created_at']),
            models.Index(fields=['resolved']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.severity}] {self.service}: {self.message[:100]}'


class ScheduledTask(models.Model):
    """Track scheduled/cron job executions."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('timeout', 'Timeout'),
    ]

    task_name = models.CharField(max_length=200, verbose_name='Nama Task')
    task_type = models.CharField(max_length=100, verbose_name='Tipe Task')
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending',
        verbose_name='Status'
    )
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='Mulai')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='Selesai')
    duration_ms = models.IntegerField(default=0, verbose_name='Durasi (ms)')
    result = models.JSONField(default=dict, blank=True, verbose_name='Hasil')
    error_message = models.TextField(blank=True, null=True, verbose_name='Error')
    is_scheduled = models.BooleanField(default=True, verbose_name='Terjadwal')
    cron_expression = models.CharField(max_length=100, blank=True, null=True, verbose_name='Cron')
    next_run = models.DateTimeField(null=True, blank=True, verbose_name='Jalan Lagi')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'scheduled_tasks'
        verbose_name = 'Tugas Terjadwal'
        verbose_name_plural = 'Tugas Terjadwal'
        indexes = [
            models.Index(fields=['task_name']),
            models.Index(fields=['status']),
            models.Index(fields=['-started_at']),
        ]
        ordering = ['-started_at']

    def __str__(self):
        return f'{self.task_name}: {self.status}'
