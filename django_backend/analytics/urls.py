"""
Analytics URL configuration for Warungio Marketplace.
"""

from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.DashboardSummaryView.as_view(), name='dashboard-summary'),
    path('sales/', views.SalesAnalyticsView.as_view(), name='sales-analytics'),
    path('sales/trend/', views.SalesTrendDataView.as_view(), name='sales-trend'),
    path('devices/', views.DeviceAnalyticsView.as_view(), name='device-analytics'),
    path('activities/', views.UserActivityView.as_view(), name='user-activities'),
    path('reports/', views.DailyReportView.as_view(), name='daily-reports'),
    path('seller-report/', views.SellerReportView.as_view(), name='seller-report'),
    path('realtime/', views.RealTimeAnalyticsView.as_view(), name='realtime-analytics'),
]
