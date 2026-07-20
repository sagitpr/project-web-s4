"""
API Views for Engagement & Retention Engine.
Provides REST endpoints for engagement metrics, notifications, and admin dashboard.
"""

import logging
from datetime import timedelta, datetime
from typing import Dict, Any

from rest_framework import status, permissions, views, generics, viewsets, mixins
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Count, Sum, Avg, Q
from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404

from accounts.permissions import IsBuyer, IsSeller, IsAdmin
from engagement.models import (
    UserBehaviorProfile, BehaviorEvent, ActivityLog,
    ChurnPrediction, DeviceToken, NotificationTemplate,
    NotificationCampaign, NotificationQueue, NotificationAnalytics,
    NotificationDeliveryLog, NotificationABTest, QuietHoursConfig,
    NotificationPreferenceExtension, NotificationCooldown, EngagementSignal,
)
from engagement.serializers import (
    UserBehaviorProfileSerializer, BehaviorEventSerializer, ActivityLogSerializer,
    ChurnPredictionSerializer, DeviceTokenSerializer, DeviceTokenRegisterSerializer,
    NotificationTemplateSerializer, NotificationCampaignSerializer,
    NotificationQueueSerializer, NotificationAnalyticsSerializer,
    NotificationDeliveryLogSerializer, NotificationABTestSerializer,
    QuietHoursConfigSerializer, NotificationPreferenceExtensionSerializer,
    EngagementSignalSerializer, EngagementDashboardSerializer, UserEngagementSummarySerializer,
)
from engagement.services.scoring_engine import get_scoring_engine
from engagement.services.ai_generator import get_ai_notification_generator
from engagement.services.timing_engine import get_timing_engine
from engagement.services.notification_intelligence import get_notification_intelligence
from engagement.services.push_service import get_push_service
from drf_spectacular.utils import extend_schema

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# USER ENGAGEMENT PROFILE
# ═══════════════════════════════════════════════════════════════

@extend_schema(exclude=True)
class UserEngagementProfileView(views.APIView):
    """Get the current user's engagement profile and all scores."""
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        from engagement.models import UserBehaviorProfile, ChurnPrediction

        profile, _ = UserBehaviorProfile.objects.get_or_create(user=request.user)
        serializer = UserBehaviorProfileSerializer(profile)
        data = serializer.data

        # Add churn prediction
        try:
            churn = ChurnPrediction.objects.get(user=request.user)
            data['churn_prediction'] = ChurnPredictionSerializer(churn).data
        except ChurnPrediction.DoesNotExist:
            data['churn_prediction'] = None

        return Response(data)


class UserBehaviorEventsView(generics.ListAPIView):
    """List the current user's behavior events."""
    serializer_class = BehaviorEventSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return super().get_queryset().none()

        qs = BehaviorEvent.objects.filter(user=self.request.user)

        # Filter by event_type
        event_type = self.request.query_params.get('event_type')
        if event_type:
            qs = qs.filter(event_type=event_type)

        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(event_category=category)

        # Date range
        days = self.request.query_params.get('days')
        if days:
            try:
                cutoff = timezone.now() - timedelta(days=int(days))
                qs = qs.filter(event_time__gte=cutoff)
            except ValueError:
                pass

        return qs.order_by('-event_time')[:100]


@extend_schema(exclude=True)
class RecordBehaviorEventView(views.APIView):
    """Record a behavior event for the current user."""
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        event_type = request.data.get('event_type', '').strip()
        if not event_type:
            return Response({'error': 'event_type is required'}, status=status.HTTP_400_BAD_REQUEST)

        from engagement.signals import _record_behavior_event
        _record_behavior_event(
            request.user,
            event_type=event_type,
            event_category=request.data.get('event_category', ''),
            data=request.data.get('data', {}),
            value=request.data.get('value'),
            source=request.data.get('source', 'api'),
            request=request,
        )

        return Response({'status': 'recorded', 'event_type': event_type})


@extend_schema(exclude=True)
class RefreshEngagementScoresView(views.APIView):
    """Manually refresh all engagement scores for the current user."""
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        engine = get_scoring_engine()
        scores = engine.update_full_profile(request.user)
        return Response({
            'status': 'refreshed',
            'scores': scores,
        })


class UserActivityLogView(generics.ListAPIView):
    """Get the current user's activity logs."""
    serializer_class = ActivityLogSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        qs = ActivityLog.objects.filter(user=self.request.user)

        period = self.request.query_params.get('period')
        if period in ('daily', 'weekly', 'monthly'):
            qs = qs.filter(period=period)

        days = self.request.query_params.get('days', 30)
        try:
            cutoff = timezone.now() - timedelta(days=int(days))
            qs = qs.filter(period_start__gte=cutoff)
        except ValueError:
            pass

        return qs.order_by('-period_start')[:90]


# ═══════════════════════════════════════════════════════════════
# DEVICE TOKENS
# ═══════════════════════════════════════════════════════════════

@extend_schema(exclude=True)
class DeviceTokenView(views.APIView):
    """Register or unregister device tokens for push notifications."""
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        """Register a device token."""
        serializer = DeviceTokenRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        push_service = get_push_service()
        token = push_service.register_device_token(
            user=request.user,
            token=serializer.validated_data['token'],
            platform=serializer.validated_data['platform'],
            device_name=serializer.validated_data.get('device_name', ''),
            device_id=serializer.validated_data.get('device_id', ''),
            app_version=serializer.validated_data.get('app_version', ''),
        )

        return Response(DeviceTokenSerializer(token).data, status=status.HTTP_201_CREATED)

    def delete(self, request):
        """Unregister a device token."""
        token = request.data.get('token', '')
        platform = request.data.get('platform', '')

        if not token:
            return Response({'error': 'token is required'}, status=status.HTTP_400_BAD_REQUEST)

        push_service = get_push_service()
        push_service.unregister_device_token(token, platform)

        return Response({'status': 'unregistered'})


class DeviceTokenListView(generics.ListAPIView):
    """List the current user's registered device tokens."""
    serializer_class = DeviceTokenSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return DeviceToken.objects.filter(user=self.request.user, is_active=True)


# ═══════════════════════════════════════════════════════════════
# AI NOTIFICATION GENERATION
# ═══════════════════════════════════════════════════════════════

@extend_schema(exclude=True)
class AINotificationGenerateView(views.APIView):
    """Generate an AI-powered notification for the current user."""
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        trigger_type = request.data.get('trigger_type', 'personalization')
        context = request.data.get('context', {})

        generator = get_ai_notification_generator()
        result = generator.generate(request.user, trigger_type, context)

        if not result:
            return Response(
                {'error': 'Failed to generate notification'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(result)


@extend_schema(exclude=True)
class AIEnqueueNotificationView(views.APIView):
    """Generate and enqueue an AI notification for intelligent delivery."""
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        trigger_type = request.data.get('trigger_type', 'personalization')
        context = request.data.get('context', {})

        intelligence = get_notification_intelligence()
        queue_item = intelligence.enqueue_ai_notification(
            user=request.user,
            trigger_type=trigger_type,
            context=context,
            priority=request.data.get('priority', 1),
        )

        if not queue_item:
            return Response(
                {'error': 'Failed to enqueue notification', 'status': 'rejected'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({
            'id': queue_item.id,
            'title': queue_item.title,
            'body': queue_item.body,
            'status': queue_item.status,
            'scheduled_for': queue_item.scheduled_for,
            'psychological_trigger': queue_item.psychological_trigger,
            'ai_generated': queue_item.ai_generated,
        })


# ═══════════════════════════════════════════════════════════════
# NOTIFICATION QUEUE
# ═══════════════════════════════════════════════════════════════

class UserNotificationQueueView(generics.ListAPIView):
    """List the current user's queued notifications."""
    serializer_class = NotificationQueueSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        qs = NotificationQueue.objects.filter(user=self.request.user)

        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        return qs.order_by('-created_at')[:50]


@extend_schema(exclude=True)
class MarkNotificationOpenedView(views.APIView):
    """Mark a notification as opened by the user."""
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, queue_id):
        item = get_object_or_404(NotificationQueue, id=queue_id, user=request.user)
        item.opened_at = timezone.now()
        item.status = 'opened'
        item.save(update_fields=['opened_at', 'status'])

        # Track on user profile
        UserBehaviorProfile.objects.filter(user=request.user).update(
            total_notifications_opened=F('total_notifications_opened') + 1,
        )

        return Response({'status': 'opened'})


@extend_schema(exclude=True)
class MarkNotificationClickedView(views.APIView):
    """Mark a notification as clicked by the user."""
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, queue_id):
        item = get_object_or_404(NotificationQueue, id=queue_id, user=request.user)
        item.clicked_at = timezone.now()
        if not item.opened_at:
            item.opened_at = timezone.now()
        item.save(update_fields=['clicked_at', 'opened_at', 'status'])

        # Track on user profile
        UserBehaviorProfile.objects.filter(user=request.user).update(
            total_notifications_opened=F('total_notifications_opened') + 1,
            total_notification_clicks=F('total_notification_clicks') + 1,
        )

        return Response({'status': 'clicked'})


# ═══════════════════════════════════════════════════════════════
# NOTIFICATION PREFERENCES
# ═══════════════════════════════════════════════════════════════

class ExtendedPreferenceView(generics.RetrieveUpdateAPIView):
    """Get/update extended notification preferences."""
    serializer_class = NotificationPreferenceExtensionSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        obj, created = NotificationPreferenceExtension.objects.get_or_create(
            user=self.request.user
        )
        return obj


class QuietHoursView(generics.RetrieveUpdateAPIView):
    """Get/update quiet hours configuration."""
    serializer_class = QuietHoursConfigSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        obj, created = QuietHoursConfig.objects.get_or_create(user=self.request.user)
        return obj


# ═══════════════════════════════════════════════════════════════
# ADMIN DASHBOARD
# ═══════════════════════════════════════════════════════════════

@extend_schema(exclude=True)
class EngagementDashboardView(views.APIView):
    """Admin dashboard overview with engagement metrics."""
    permission_classes = (permissions.IsAdminUser,)

    def get(self, request):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # User stats
        total_users = User.objects.filter(is_active=True).count()
        at_risk = UserBehaviorProfile.objects.filter(
            risk_level__in=['at_risk', 'dormant', 'churned']
        ).count()
        dormant = UserBehaviorProfile.objects.filter(risk_level='dormant').count()

        # Average scores
        avg_scores = UserBehaviorProfile.objects.aggregate(
            avg_engagement=Avg('engagement_score'),
            avg_retention=Avg('retention_score'),
            avg_churn=Avg('churn_risk_score'),
            avg_loyalty=Avg('loyalty_score'),
        )

        # Notification stats today
        queue_stats = NotificationQueue.objects.aggregate(
            total_queued=Count('id'),
            total_delivered_today=Count('id', filter=Q(
                status='delivered', delivered_at__gte=today_start
            )),
        )

        # Delivery logs today
        logs_today = NotificationDeliveryLog.objects.filter(
            created_at__gte=today_start
        )
        total_sent = logs_today.count()
        total_delivered = logs_today.filter(status='delivered').count()
        total_opened = logs_today.filter(status='opened').count()

        delivery_rate = total_delivered / max(total_sent, 1)
        open_rate = total_opened / max(total_delivered, 1)

        # Queue health
        queue_health = {
            'queued': NotificationQueue.objects.filter(status='queued').count(),
            'scheduled': NotificationQueue.objects.filter(status='scheduled').count(),
            'delivering': NotificationQueue.objects.filter(status='delivering').count(),
            'failed': NotificationQueue.objects.filter(status='failed').count(),
            'rate_limited': NotificationQueue.objects.filter(status='rate_limited').count(),
            'quiet_hours': NotificationQueue.objects.filter(status='quiet_hours').count(),
        }

        data = {
            'total_active_users': total_users,
            'total_at_risk_users': at_risk,
            'total_dormant_users': dormant,
            'avg_engagement_score': round(float(avg_scores['avg_engagement'] or 0), 2),
            'avg_retention_score': round(float(avg_scores['avg_retention'] or 0), 2),
            'avg_churn_risk': round(float(avg_scores['avg_churn'] or 0), 2),
            'avg_loyalty_score': round(float(avg_scores['avg_loyalty'] or 0), 2),
            'total_queued_notifications': queue_stats['total_queued'] or 0,
            'total_delivered_today': queue_stats['total_delivered_today'] or 0,
            'delivery_rate': round(delivery_rate, 4),
            'open_rate': round(open_rate, 4),
            'ctr': round(open_rate * 0.6, 4),  # Estimated CTR from open rate
            'queue_health': queue_health,
        }

        return Response(data)


@extend_schema(exclude=True)
class UserEngagementListView(views.APIView):
    """Admin: List all users with their engagement profiles."""
    permission_classes = (permissions.IsAdminUser,)

    def get(self, request):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        limit = int(request.query_params.get('limit', 200))
        offset = int(request.query_params.get('offset', 0))
        risk_filter = request.query_params.get('risk_level', '')

        users = User.objects.filter(is_active=True).select_related(
            'behavior_profile'
        ).order_by('-date_joined')

        if risk_filter:
            users = users.filter(behavior_profile__risk_level=risk_filter)

        users = users[offset:offset + limit]

        results = []
        for user in users:
            profile = getattr(user, 'behavior_profile', None)
            churn = None
            try:
                churn = user.churn_prediction
            except Exception:
                pass

            results.append({
                'user_id': user.id,
                'email': user.email,
                'full_name': user.full_name,
                'role': user.role,
                'engagement_score': getattr(profile, 'engagement_score', 0),
                'activity_score': getattr(profile, 'activity_score', 0),
                'retention_score': getattr(profile, 'retention_score', 0),
                'loyalty_score': getattr(profile, 'loyalty_score', 0),
                'churn_risk_score': getattr(profile, 'churn_risk_score', 0),
                'fatigue_score': getattr(profile, 'notification_fatigue_score', 0),
                'risk_level': getattr(profile, 'risk_level', 'active'),
                'last_active': getattr(profile, 'last_active_at', None),
                'total_orders': getattr(profile, 'total_orders', 0),
                'total_notifications_sent': getattr(profile, 'total_notifications_sent', 0),
                'notification_open_rate': getattr(profile, 'notification_open_rate', 0),
                'optimal_hour': getattr(profile, 'optimal_notification_hour', 10),
                'churn_probability': churn.churn_probability if churn else None,
                'churn_category': churn.churn_risk_category if churn else None,
            })

        return Response({
            'results': results,
            'total': len(results),
            'limit': limit,
            'offset': offset,
        })


class NotificationQueueAdminView(generics.ListAPIView):
    """Admin: View notification queue with filtering."""
    serializer_class = NotificationQueueSerializer
    permission_classes = (permissions.IsAdminUser,)

    def get_queryset(self):
        qs = NotificationQueue.objects.select_related('user').all()

        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        trigger_filter = self.request.query_params.get('trigger_type')
        if trigger_filter:
            qs = qs.filter(trigger_type=trigger_filter)

        return qs.order_by('-created_at')[:100]


class CampaignViewSet(viewsets.ModelViewSet):
    """Admin: CRUD for notification campaigns."""
    queryset = NotificationCampaign.objects.all().order_by('-created_at')
    serializer_class = NotificationCampaignSerializer
    permission_classes = (permissions.IsAdminUser,)

    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """Manually execute a campaign."""
        from engagement.tasks import execute_campaign_task
        campaign = self.get_object()
        execute_campaign_task.delay(campaign.id)
        return Response({'status': 'execution_started', 'campaign_id': campaign.id})

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """Pause a running campaign."""
        campaign = self.get_object()
        if campaign.status == 'running':
            campaign.status = 'paused'
            campaign.save(update_fields=['status'])
            return Response({'status': 'paused'})
        return Response({'error': 'Campaign is not running'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """Resume a paused campaign."""
        campaign = self.get_object()
        if campaign.status == 'paused':
            campaign.status = 'running'
            campaign.save(update_fields=['status'])
            return Response({'status': 'resumed'})
        return Response({'error': 'Campaign is not paused'}, status=status.HTTP_400_BAD_REQUEST)


class TemplateViewSet(viewsets.ModelViewSet):
    """Admin: CRUD for notification templates."""
    queryset = NotificationTemplate.objects.all().order_by('name')
    serializer_class = NotificationTemplateSerializer
    permission_classes = (permissions.IsAdminUser,)


class ABTestViewSet(viewsets.ModelViewSet):
    """Admin: CRUD for A/B tests."""
    queryset = NotificationABTest.objects.all().order_by('-created_at')
    serializer_class = NotificationABTestSerializer
    permission_classes = (permissions.IsAdminUser,)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start an A/B test."""
        test = self.get_object()
        if test.status == 'draft':
            test.status = 'running'
            test.started_at = timezone.now()
            test.save(update_fields=['status', 'started_at'])
            return Response({'status': 'started'})
        return Response({'error': 'Test is not in draft status'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete an A/B test and determine winner."""
        test = self.get_object()
        if test.status != 'running':
            return Response({'error': 'Test is not running'}, status=status.HTTP_400_BAD_REQUEST)

        test.status = 'completed'
        test.completed_at = timezone.now()

        # Determine winner (simplified - would need statistical analysis in production)
        variant_results = {}
        if test.results:
            variant_results = test.results

        if variant_results:
            winner = max(variant_results, key=lambda v: variant_results[v].get('open_rate', 0))
            test.winning_variant = winner

        test.save()
        return Response({'status': 'completed', 'winning_variant': test.winning_variant})


@extend_schema(exclude=True)
class AnalyticsView(views.APIView):
    """Admin: View notification analytics."""
    permission_classes = (permissions.IsAdminUser,)

    def get(self, request):
        period = request.query_params.get('period', 'weekly')

        analytics = NotificationAnalytics.objects.filter(
            period=period,
        ).order_by('-period_start')[:30]

        # Aggregate
        total_data = analytics.aggregate(
            total_sent=Sum('total_sent'),
            total_delivered=Sum('total_delivered'),
            total_opened=Sum('total_opened'),
            total_clicked=Sum('total_clicked'),
        )

        data = {
            'period': period,
            'aggregated': {
                'total_sent': total_data['total_sent'] or 0,
                'total_delivered': total_data['total_delivered'] or 0,
                'total_opened': total_data['total_opened'] or 0,
                'total_clicked': total_data['total_clicked'] or 0,
                'delivery_rate': round((total_data['total_delivered'] or 0) / max(total_data['total_sent'] or 0, 1), 4),
                'open_rate': round((total_data['total_opened'] or 0) / max(total_data['total_delivered'] or 0, 1), 4),
            },
            'trends': NotificationAnalyticsSerializer(analytics, many=True).data,
        }

        return Response(data)


class EngagementSignalViewSet(viewsets.ModelViewSet):
    """Admin: CRUD for engagement signals."""
    queryset = EngagementSignal.objects.all().order_by('name')
    serializer_class = EngagementSignalSerializer
    permission_classes = (permissions.IsAdminUser,)


# ═══════════════════════════════════════════════════════════════
# HEALTH CHECK
# ═══════════════════════════════════════════════════════════════

@extend_schema(exclude=True)
class EngagementHealthView(views.APIView):
    """Health check for the engagement engine."""
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        from django.db import connection

        results = {
            'status': 'ok',
            'service': 'engagement_engine',
        }

        try:
            # Check database connectivity
            profile_count = UserBehaviorProfile.objects.count()
            queue_count = NotificationQueue.objects.count()
            results['database'] = {
                'status': 'connected',
                'profiles': profile_count,
                'queue_items': queue_count,
            }
        except Exception as e:
            results['database'] = {'status': 'error', 'message': str(e)}
            results['status'] = 'degraded'

        # Check Gemini connectivity
        try:
            from ai_services.gemini_client import get_gemini_client
            client = get_gemini_client()
            results['gemini'] = {
                'status': 'configured' if client.api_key else 'not_configured',
            }
        except Exception as e:
            results['gemini'] = {'status': 'error', 'message': str(e)}

        return Response(results)


from django.db.models import F
