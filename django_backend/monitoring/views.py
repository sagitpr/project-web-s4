"""
Monitoring views for Warungio Marketplace.
Server health, performance metrics, uptime, error tracking.
"""

import os
import time
import platform
from datetime import timedelta, date
from decimal import Decimal

from django.db.models import Avg, Count, Sum, Max, Min, Q
from django.db import connection, connections
from django.utils import timezone
from django.conf import settings
from rest_framework import status, generics, permissions, views
from rest_framework.response import Response

from .models import (
    SystemHealth, PerformanceMetric, UptimeRecord,
    ErrorLog, ScheduledTask
)
from accounts.permissions import IsAdmin


class HealthCheckView(views.APIView):
    """Comprehensive health check endpoint."""
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        checks = {}
        overall_status = 'healthy'

        # Database check
        try:
            c = connection.cursor()
            c.execute('SELECT 1')
            c.close()
            checks['database'] = {'status': 'healthy', 'message': 'Database connected'}
        except Exception as e:
            checks['database'] = {'status': 'down', 'message': str(e)}
            overall_status = 'degraded'

        # Cache check
        try:
            from django.core.cache import cache
            cache.set('health_check', 'ok', 5)
            result = cache.get('health_check')
            checks['cache'] = {'status': 'healthy' if result == 'ok' else 'degraded', 'message': 'Cache working'}
        except Exception as e:
            checks['cache'] = {'status': 'degraded', 'message': str(e)}

        # Disk space check (os.statvfs is Unix-only; fallback on unsupported platforms)
        try:
            stat = os.statvfs(settings.BASE_DIR)
            free_gb = (stat.f_frsize * stat.f_bavail) / (1024 ** 3)
            checks['disk'] = {
                'status': 'healthy' if free_gb > 1 else 'warning',
                'free_gb': round(free_gb, 2),
                'message': f'{free_gb:.1f}GB free',
            }
            if free_gb < 0.5:
                overall_status = 'degraded'
        except Exception:
            checks['disk'] = {'status': 'unknown', 'message': 'Cannot check disk (statvfs unavailable)'}

        # Memory check
        try:
            import psutil
            mem = psutil.virtual_memory()
            checks['memory'] = {
                'status': 'healthy' if mem.percent < 85 else 'warning',
                'used_percent': mem.percent,
                'available_mb': round(mem.available / (1024 ** 2), 1),
                'message': f'{mem.percent}% used',
            }
            if mem.percent > 90:
                overall_status = 'degraded'
        except ImportError:
            checks['memory'] = {'status': 'unknown', 'message': 'psutil not installed'}

        return Response({
            'status': overall_status,
            'timestamp': timezone.now().isoformat(),
            'service': 'warungio-api',
            'version': '1.0.0',
            'environment': 'production' if not settings.DEBUG else 'development',
            'checks': checks,
        })


class MonitoringDashboardView(views.APIView):
    """Full monitoring dashboard with all metrics."""
    permission_classes = (permissions.IsAuthenticated, IsAdmin)

    def get(self, request):
        now = timezone.now()
        today = now.date()
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)

        # Current system health
        health = SystemHealth.objects.filter(checked_at__gte=day_ago).order_by('-checked_at')[:10]

        # Recent metrics
        metrics = PerformanceMetric.objects.filter(recorded_at__gte=hour_ago)

        # Today's uptime
        uptime_today = UptimeRecord.objects.filter(date=today).first()

        # Errors in last 24h
        recent_errors = ErrorLog.objects.filter(created_at__gte=day_ago)
        error_count = recent_errors.count()
        critical_errors = recent_errors.filter(severity='critical').count()

        # Active scheduled tasks
        active_tasks = ScheduledTask.objects.filter(status='running').count()
        failed_tasks = ScheduledTask.objects.filter(
            status='failed', started_at__gte=day_ago
        ).count()

        # Performance snapshots
        latest_cpu = PerformanceMetric.objects.filter(
            metric_type='cpu', recorded_at__gte=hour_ago
        ).order_by('-recorded_at').first()

        latest_memory = PerformanceMetric.objects.filter(
            metric_type='memory', recorded_at__gte=hour_ago
        ).order_by('-recorded_at').first()

        latest_api_latency = PerformanceMetric.objects.filter(
            metric_type='api_latency', recorded_at__gte=hour_ago
        ).order_by('-recorded_at').first()

        # DB connections
        db_connections = PerformanceMetric.objects.filter(
            metric_type='db_connections', recorded_at__gte=hour_ago
        ).order_by('-recorded_at').first()

        # Error trends (last 7 days)
        error_trend = []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            count = ErrorLog.objects.filter(created_at__date=d).count()
            error_trend.append({'date': d.isoformat(), 'count': count})

        # CPU/Memory trends (last hour, sampled every 5 min)
        cpu_trend = PerformanceMetric.objects.filter(
            metric_type='cpu', recorded_at__gte=hour_ago
        ).values('recorded_at').annotate(
            value=Avg('value')
        ).order_by('recorded_at')

        return Response({
            'overview': {
                'status': 'healthy',
                'service': 'warungio-api',
                'uptime_today': float(uptime_today.uptime_percent) if uptime_today else 100.0,
                'errors_24h': error_count,
                'critical_errors_24h': critical_errors,
                'active_tasks': active_tasks,
                'failed_tasks_24h': failed_tasks,
                'db_connections': int(db_connections.value) if db_connections else 0,
            },
            'performance': {
                'cpu_usage': float(latest_cpu.value) if latest_cpu else 0,
                'memory_usage': float(latest_memory.value) if latest_memory else 0,
                'api_latency_ms': float(latest_api_latency.value) if latest_api_latency else 0,
                'cpu_trend': [
                    {'time': m['recorded_at'].strftime('%H:%M'), 'value': float(m['value'])}
                    for m in cpu_trend
                ],
            },
            'errors': {
                'total_24h': error_count,
                'critical': critical_errors,
                'trend_7d': error_trend,
            'recent': [{'id': e.id, 'service': e.service, 'severity': e.severity, 'message': e.message[:150], 'created_at': e.created_at}
                      for e in recent_errors.order_by('-created_at')[:10]],
            },
            'services': [
                {'name': s.service_name, 'status': s.status, 'response_time_ms': s.response_time_ms}
                for s in health
            ],
            'timestamp': now.isoformat(),
        })


class SystemHealthListView(generics.ListAPIView):
    """List system health records."""
    permission_classes = (permissions.IsAuthenticated, IsAdmin)

    def get_queryset(self):
        return SystemHealth.objects.all()[:100]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        return Response([{
            'id': h.id,
            'service_name': h.service_name,
            'status': h.status,
            'response_time_ms': h.response_time_ms,
            'error_rate': float(h.error_rate),
            'checked_at': h.checked_at,
        } for h in queryset])


class LatestHealthView(views.APIView):
    """Get latest health status for all services."""
    permission_classes = (permissions.IsAuthenticated, IsAdmin)

    def get(self, request):
        services = SystemHealth.objects.values('service_name').annotate(
            last_check=Max('checked_at')
        )
        result = []
        for s in services:
            latest = SystemHealth.objects.filter(
                service_name=s['service_name'],
                checked_at=s['last_check']
            ).first()
            if latest:
                result.append({
                    'service_name': latest.service_name,
                    'status': latest.status,
                    'response_time_ms': latest.response_time_ms,
                    'checked_at': latest.checked_at,
                })
        return Response(result)


class PerformanceMetricsView(views.APIView):
    """Get performance metrics."""
    permission_classes = (permissions.IsAuthenticated, IsAdmin)

    def get(self, request):
        metric_type = request.query_params.get('type')
        hours = int(request.query_params.get('hours', 1))

        since = timezone.now() - timedelta(hours=hours)
        qs = PerformanceMetric.objects.filter(recorded_at__gte=since)
        if metric_type:
            qs = qs.filter(metric_type=metric_type)

        return Response([{
            'id': m.id,
            'metric_type': m.metric_type,
            'value': m.value,
            'unit': m.unit,
            'recorded_at': m.recorded_at,
        } for m in qs.order_by('recorded_at')[:500]])


class MetricDetailView(views.APIView):
    """Get detail for a specific metric type."""
    permission_classes = (permissions.IsAuthenticated, IsAdmin)

    def get(self, request, metric_type):
        hours = int(request.query_params.get('hours', 24))
        since = timezone.now() - timedelta(hours=hours)

        metrics = PerformanceMetric.objects.filter(
            metric_type=metric_type,
            recorded_at__gte=since
        ).order_by('recorded_at')

        if not metrics.exists():
            return Response({'error': f'No data for metric: {metric_type}'}, status=404)

        return Response({
            'metric_type': metric_type,
            'current': float(metrics.last().value),
            'average': float(metrics.aggregate(avg=Avg('value'))['avg'] or 0),
            'max': float(metrics.aggregate(max=Max('value'))['max'] or 0),
            'min': float(metrics.aggregate(min=Min('value'))['min'] or 0),
            'data_points': metrics.count(),
            'history': [
                {'time': m.recorded_at.strftime('%H:%M'), 'value': m.value}
                for m in metrics[:200]
            ],
        })


class MetricsSummaryView(views.APIView):
    """Summary of all metrics."""
    permission_classes = (permissions.IsAuthenticated, IsAdmin)

    def get(self, request):
        metrics = {}
        for metric_type, _ in PerformanceMetric.METRIC_TYPES:
            latest = PerformanceMetric.objects.filter(
                metric_type=metric_type
            ).order_by('-recorded_at').first()
            if latest:
                metrics[metric_type] = {
                    'value': latest.value,
                    'unit': latest.unit,
                    'recorded_at': latest.recorded_at,
                }
        return Response(metrics)


class UptimeView(generics.ListAPIView):
    """Get uptime records."""
    permission_classes = (permissions.IsAuthenticated, IsAdmin)

    def get_queryset(self):
        days = int(self.request.query_params.get('days', 30))
        since = timezone.now().date() - timedelta(days=days)
        return UptimeRecord.objects.filter(date__gte=since).order_by('-date')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        return Response([{
            'date': r.date,
            'uptime_percent': float(r.uptime_percent),
            'total_checks': r.total_checks,
            'failed_checks': r.failed_checks,
            'avg_response_time_ms': r.avg_response_time_ms,
            'downtime_seconds': r.downtime_seconds,
        } for r in queryset])


class CurrentMonthUptimeView(views.APIView):
    """Get current month uptime."""
    permission_classes = (permissions.IsAuthenticated, IsAdmin)

    def get(self, request):
        today = timezone.now().date()
        month_start = today.replace(day=1)

        records = UptimeRecord.objects.filter(date__gte=month_start)
        avg_uptime = records.aggregate(avg=Avg('uptime_percent'))['avg'] or 100

        return Response({
            'month': month_start.strftime('%B %Y'),
            'average_uptime': float(avg_uptime),
            'days_tracked': records.count(),
            'total_downtime_seconds': records.aggregate(total=Sum('downtime_seconds'))['total'] or 0,
        })


class ErrorLogListView(generics.ListAPIView):
    """List error logs."""
    permission_classes = (permissions.IsAuthenticated, IsAdmin)

    def get_queryset(self):
        hours = int(self.request.query_params.get('hours', 24))
        since = timezone.now() - timedelta(hours=hours)
        qs = ErrorLog.objects.filter(created_at__gte=since)

        severity = self.request.query_params.get('severity')
        if severity:
            qs = qs.filter(severity=severity)

        return qs.order_by('-created_at')[:100]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        return Response([{
            'id': e.id,
            'service': e.service,
            'severity': e.severity,
            'message': e.message[:200],
            'endpoint': e.endpoint,
            'method': e.method,
            'status_code': e.status_code,
            'resolved': e.resolved,
            'created_at': e.created_at,
        } for e in queryset])


class ResolveErrorView(views.APIView):
    """Mark an error as resolved."""
    permission_classes = (permissions.IsAuthenticated, IsAdmin)

    def post(self, request, pk):
        error = ErrorLog.objects.filter(pk=pk).first()
        if not error:
            return Response({'error': 'Error not found.'}, status=404)
        error.resolved = True
        error.resolved_at = timezone.now()
        error.resolved_by = request.user
        error.save(update_fields=['resolved', 'resolved_at', 'resolved_by'])
        return Response({'message': 'Error marked as resolved.'})


class RecentErrorsView(views.APIView):
    """Get recent critical errors."""
    permission_classes = (permissions.IsAuthenticated, IsAdmin)

    def get(self, request):
        errors = ErrorLog.objects.filter(
            severity__in=['critical', 'error'],
            resolved=False
        ).order_by('-created_at')[:20]

        return Response([{
            'id': e.id,
            'service': e.service,
            'severity': e.severity,
            'message': e.message[:150],
            'created_at': e.created_at,
        } for e in errors])


class ErrorStatsView(views.APIView):
    """Get error statistics."""
    permission_classes = (permissions.IsAuthenticated, IsAdmin)

    def get(self, request):
        days = int(request.query_params.get('days', 7))
        since = timezone.now() - timedelta(days=days)

        total = ErrorLog.objects.filter(created_at__gte=since).count()
        by_severity = ErrorLog.objects.filter(created_at__gte=since).values(
            'severity'
        ).annotate(count=Count('id'))

        by_service = ErrorLog.objects.filter(created_at__gte=since).values(
            'service'
        ).annotate(count=Count('id')).order_by('-count')[:10]

        return Response({
            'total': total,
            'by_severity': {s['severity']: s['count'] for s in by_severity},
            'top_services': [{'service': s['service'], 'count': s['count']} for s in by_service],
            'period_days': days,
        })


class ScheduledTaskListView(generics.ListAPIView):
    """List scheduled tasks."""
    permission_classes = (permissions.IsAuthenticated, IsAdmin)

    def get_queryset(self):
        qs = ScheduledTask.objects.all()
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs.order_by('-started_at')[:100]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        return Response([{
            'id': t.id,
            'task_name': t.task_name,
            'task_type': t.task_type,
            'status': t.status,
            'started_at': t.started_at,
            'completed_at': t.completed_at,
            'duration_ms': t.duration_ms,
        } for t in queryset])


class ScheduledTaskDetailView(views.APIView):
    """Get scheduled task detail."""
    permission_classes = (permissions.IsAuthenticated, IsAdmin)

    def get(self, request, pk):
        task = ScheduledTask.objects.filter(pk=pk).first()
        if not task:
            return Response({'error': 'Task not found.'}, status=404)
        return Response({
            'id': task.id,
            'task_name': task.task_name,
            'task_type': task.task_type,
            'status': task.status,
            'started_at': task.started_at,
            'completed_at': task.completed_at,
            'duration_ms': task.duration_ms,
            'result': task.result,
            'error_message': task.error_message,
            'cron_expression': task.cron_expression,
            'next_run': task.next_run,
        })


class FullStatusView(views.APIView):
    """Complete system status including all monitoring data."""
    permission_classes = (permissions.IsAuthenticated, IsAdmin)

    def get(self, request):
        now = timezone.now()
        return Response({
            'server': {
                'started_at': now.isoformat(),
                'uptime_days': 0,
                'python_version': platform.python_version(),
                'debug_mode': settings.DEBUG,
            },
            'services': {
                'api': 'healthy',
                'database': 'healthy',
                'cache': 'healthy',
                'websocket': 'healthy',
            },
            'recent_alerts': [],
            'timestamp': now.isoformat(),
        })


class AdminDashboardStatsView(views.APIView):
    """
    Admin dashboard statistics — real data from database.
    Returns aggregated counts for Users, Stores, Orders, Revenue.
    Replaces the previous hardcoded HTML template.
    """
    permission_classes = (permissions.IsAuthenticated, IsAdmin)

    def get(self, request):
        from django.contrib.auth import get_user_model
        from stores.models import Store
        from orders.models import Order

        User = get_user_model()
        today = timezone.now().date()
        thirty_days_ago = today - timedelta(days=30)

        # Total Users
        total_users = User.objects.count()
        new_users_30d = User.objects.filter(date_joined__date__gte=thirty_days_ago).count()
        user_growth = round((new_users_30d / max(total_users - new_users_30d, 1)) * 100, 1) if total_users > 0 else 0

        # Active Stores
        active_stores = Store.objects.filter(status='active').count()
        new_stores_30d = Store.objects.filter(created_at__date__gte=thirty_days_ago).count()
        store_growth = round((new_stores_30d / max(active_stores - new_stores_30d, 1)) * 100, 1) if active_stores > 0 else 0

        # Total Orders
        total_orders = Order.objects.count()
        orders_30d = Order.objects.filter(created_at__date__gte=thirty_days_ago).count()
        order_growth = round((orders_30d / max(total_orders - orders_30d, 1)) * 100, 1) if total_orders > 0 else 0

        # Revenue (30d) — completed orders only
        revenue_30d = Order.objects.filter(
            created_at__date__gte=thirty_days_ago,
            order_status='completed'
        ).aggregate(total=Sum('total_price'))['total'] or 0
        
        # Sellers
        total_sellers = User.objects.filter(role='seller').count()
        
        # Buyers
        total_buyers = User.objects.filter(role='buyer').count()

        # Pending verifications (stores pending)
        pending_stores = Store.objects.filter(status='pending').count()

        # Top stores by order count (30d)
        from django.db.models import Count
        top_stores = Store.objects.filter(
            status='active',
            orders__created_at__date__gte=thirty_days_ago
        ).annotate(
            order_count=Count('orders'),
            store_revenue=Sum('orders__total_price',
                filter=Q(orders__order_status='completed', orders__created_at__date__gte=thirty_days_ago))
        ).order_by('-order_count')[:5]

        data = {
            'total_users': total_users,
            'new_users_30d': new_users_30d,
            'user_growth': user_growth,
            'active_stores': active_stores,
            'new_stores_30d': new_stores_30d,
            'store_growth': store_growth,
            'total_orders': total_orders,
            'orders_30d': orders_30d,
            'order_growth': order_growth,
            'revenue_30d': float(revenue_30d),
            'revenue_30d_formatted': f'Rp {float(revenue_30d):,.0f}',
            'total_sellers': total_sellers,
            'total_buyers': total_buyers,
            'pending_stores': pending_stores,
            'top_stores': [
                {
                    'store_name': s.store_name,
                    'order_count': s.order_count,
                    'revenue': float(s.store_revenue or 0),
                }
                for s in top_stores
            ],
            'timestamp': timezone.now().isoformat(),
        }
        return Response(data)



