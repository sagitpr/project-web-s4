"""
URL Configuration for Engagement & Retention Engine API.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# ViewSets
router = DefaultRouter()
router.register(r'campaigns', views.CampaignViewSet, basename='campaign')
router.register(r'templates', views.TemplateViewSet, basename='template')
router.register(r'ab-tests', views.ABTestViewSet, basename='ab-test')
router.register(r'signals', views.EngagementSignalViewSet, basename='signal')

urlpatterns = [
    # ── User Engagement Profile ──
    path('profile/', views.UserEngagementProfileView.as_view(), name='engagement-profile'),
    path('profile/refresh/', views.RefreshEngagementScoresView.as_view(), name='engagement-refresh'),
    path('events/', views.UserBehaviorEventsView.as_view(), name='engagement-events'),
    path('events/record/', views.RecordBehaviorEventView.as_view(), name='engagement-record-event'),
    path('activity/', views.UserActivityLogView.as_view(), name='engagement-activity'),

    # ── Device Tokens ──
    path('devices/', views.DeviceTokenListView.as_view(), name='engagement-devices'),
    path('devices/register/', views.DeviceTokenView.as_view(), name='engagement-device-register'),
    path('devices/unregister/', views.DeviceTokenView.as_view(), name='engagement-device-unregister'),

    # ── AI Notifications ──
    path('ai/generate/', views.AINotificationGenerateView.as_view(), name='engagement-ai-generate'),
    path('ai/enqueue/', views.AIEnqueueNotificationView.as_view(), name='engagement-ai-enqueue'),

    # ── Notification Queue ──
    path('queue/', views.UserNotificationQueueView.as_view(), name='engagement-queue'),
    path('queue/<int:queue_id>/open/', views.MarkNotificationOpenedView.as_view(), name='engagement-notification-open'),
    path('queue/<int:queue_id>/click/', views.MarkNotificationClickedView.as_view(), name='engagement-notification-click'),

    # ── Preferences ──
    path('preferences/extended/', views.ExtendedPreferenceView.as_view(), name='engagement-preferences-extended'),
    path('preferences/quiet-hours/', views.QuietHoursView.as_view(), name='engagement-quiet-hours'),

    # ── Admin Dashboard ──
    path('admin/dashboard/', views.EngagementDashboardView.as_view(), name='engagement-admin-dashboard'),
    path('admin/users/', views.UserEngagementListView.as_view(), name='engagement-admin-users'),
    path('admin/queue/', views.NotificationQueueAdminView.as_view(), name='engagement-admin-queue'),
    path('admin/analytics/', views.AnalyticsView.as_view(), name='engagement-admin-analytics'),

    # ── ViewSets ──
    path('admin/', include(router.urls)),

    # ── Health ──
    path('health/', views.EngagementHealthView.as_view(), name='engagement-health'),
]
