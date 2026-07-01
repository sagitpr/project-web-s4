"""
Analytics URL configuration for Warungio Marketplace.
"""

from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('dashboard/', views.DashboardSummaryView.as_view(), name='dashboard-summary'),
    path('sales/', views.SalesAnalyticsView.as_view(), name='sales-analytics'),
    path('sales/trend/', views.SalesTrendDataView.as_view(), name='sales-trend'),
    path('devices/', views.DeviceAnalyticsView.as_view(), name='device-analytics'),
    path('activities/', views.UserActivityView.as_view(), name='user-activities'),
    path('reports/', views.DailyReportView.as_view(), name='daily-reports'),
    path('seller-report/', views.SellerReportView.as_view(), name='seller-report'),
    path('realtime/', views.RealTimeAnalyticsView.as_view(), name='realtime-analytics'),

    # AI Business Insights
    path('ai/insights/', views.AIBusinessInsightView.as_view(), name='ai-business-insights'),
    path('ai/quick/', views.AIQuickInsightView.as_view(), name='ai-quick-insights'),
    path('ai/growth-tips/', views.AIGrowthTipsView.as_view(), name='ai-growth-tips'),
    path('ai/admin-overview/', views.AdminAIBusinessOverviewView.as_view(), name='ai-admin-overview'),
    path('ai/mock/', views.MockAIBusinessInsightView.as_view(), name='ai-mock-insights'),
]
