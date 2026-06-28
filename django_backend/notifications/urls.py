"""
Notifications URL configuration for Warungio Marketplace.
"""

from django.urls import path
from . import views

urlpatterns = [
    path('', views.NotificationListView.as_view(), name='notification-list'),
    path('mark-read/', views.NotificationMarkReadView.as_view(), name='notification-mark-read'),
    path('unread-count/', views.NotificationUnreadCountView.as_view(), name='notification-unread-count'),
    path('preferences/', views.NotificationPreferenceView.as_view(), name='notification-preferences'),
    path('create/', views.CreateNotificationView.as_view(), name='notification-create'),
]
