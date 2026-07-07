"""
Monitoring URL configuration for Warungio Marketplace.
"""

from django.urls import path
from . import views

urlpatterns = [
    # Health Dashboard
    path('health/', views.HealthCheckView.as_view(), name='monitoring-health'),
    path('dashboard/', views.MonitoringDashboardView.as_view(), name='monitoring-dashboard'),
    
    # System Health
    path('system/', views.SystemHealthListView.as_view(), name='monitoring-system-health'),
    path('system/latest/', views.LatestHealthView.as_view(), name='monitoring-latest-health'),
    
    # Performance Metrics
    path('metrics/', views.PerformanceMetricsView.as_view(), name='monitoring-metrics'),
    path('metrics/<str:metric_type>/', views.MetricDetailView.as_view(), name='monitoring-metric-detail'),
    path('metrics/summary/', views.MetricsSummaryView.as_view(), name='monitoring-metrics-summary'),
    
    # Uptime
    path('uptime/', views.UptimeView.as_view(), name='monitoring-uptime'),
    path('uptime/current-month/', views.CurrentMonthUptimeView.as_view(), name='monitoring-current-month'),
    
    # Error Logs
    path('errors/', views.ErrorLogListView.as_view(), name='monitoring-errors'),
    path('errors/<int:pk>/resolve/', views.ResolveErrorView.as_view(), name='monitoring-error-resolve'),
    path('errors/recent/', views.RecentErrorsView.as_view(), name='monitoring-recent-errors'),
    path('errors/stats/', views.ErrorStatsView.as_view(), name='monitoring-error-stats'),
    
    # Scheduled Tasks
    path('tasks/', views.ScheduledTaskListView.as_view(), name='monitoring-tasks'),
    path('tasks/<int:pk>/', views.ScheduledTaskDetailView.as_view(), name='monitoring-task-detail'),
    
    # Full Status
    path('status/', views.FullStatusView.as_view(), name='monitoring-full-status'),
    
    # Admin Dashboard stats (real data from database)
    path('admin-stats/', views.AdminDashboardStatsView.as_view(), name='admin-dashboard-stats'),

    # Mock endpoint removed for production
]
