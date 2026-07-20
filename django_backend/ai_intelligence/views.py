"""
API Views for AI Intelligence Platform.
Provides endpoints for Digital Twin, Marketplace Health, Business Coach,
Predictions, Segmentation, Gamification, and Dashboards.
"""

import logging
from datetime import timedelta
from django.utils import timezone
from rest_framework import status, permissions, views, generics
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Count, Avg, Sum

from ai_intelligence.models import (
    DigitalTwin, MarketplaceHealthSnapshot, BusinessCoachInsight,
    PersonalShoppingInsight, DemandPrediction, PricingRecommendation,
    CustomerSegment, UserSegmentAssignment, GamificationProfile,
    Challenge, UserChallengeProgress, AIModelRegistry, ExperimentResult,
)
from drf_spectacular.utils import extend_schema
from ai_intelligence.serializers import (
    DigitalTwinSerializer, MarketplaceHealthSnapshotSerializer,
    BusinessCoachInsightSerializer, PersonalShoppingInsightSerializer,
    DemandPredictionSerializer, PricingRecommendationSerializer,
    CustomerSegmentSerializer, GamificationProfileSerializer,
    ChallengeSerializer, UserChallengeProgressSerializer,
    AIModelRegistrySerializer, ExperimentResultSerializer,
)

logger = logging.getLogger(__name__)


# ── Digital Twin ──

@extend_schema(exclude=True)
class DigitalTwinView(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        twin, _ = DigitalTwin.objects.get_or_create(user=request.user)
        return Response(DigitalTwinSerializer(twin).data)


@extend_schema(exclude=True)
class RefreshDigitalTwinView(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        from ai_intelligence.services.digital_twin import get_digital_twin_engine
        engine = get_digital_twin_engine()
        scores = engine.update_digital_twin(request.user)
        twin = DigitalTwin.objects.get(user=request.user)
        return Response({
            'status': 'refreshed',
            'twin': DigitalTwinSerializer(twin).data,
        })


# ── Marketplace Health ──

@extend_schema(exclude=True)
class MarketplaceHealthView(views.APIView):
    permission_classes = (permissions.IsAdminUser,)

    def get(self, request):
        snapshot = MarketplaceHealthSnapshot.objects.order_by('-snapshot_time').first()
        if not snapshot:
            return Response({'status': 'no_data'})
        return Response(MarketplaceHealthSnapshotSerializer(snapshot).data)


@extend_schema(exclude=True)
class MarketplaceHealthRefreshView(views.APIView):
    permission_classes = (permissions.IsAdminUser,)

    def post(self, request):
        from ai_intelligence.services.marketplace_health import get_marketplace_health_service
        service = get_marketplace_health_service()
        snapshot = service.capture_snapshot()
        return Response(MarketplaceHealthSnapshotSerializer(snapshot).data)


# ── Business Coach ──

class CoachInsightsView(generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = BusinessCoachInsightSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return BusinessCoachInsight.objects.none()

        if self.request.user.role != 'seller':
            return BusinessCoachInsight.objects.none()
        store = getattr(self.request.user, 'store', None)
        if not store:
            return BusinessCoachInsight.objects.none()
        return BusinessCoachInsight.objects.filter(store=store).order_by('-priority', '-created_at')[:20]


@extend_schema(exclude=True)
class CoachInsightReadView(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, pk):
        insight = get_object_or_404(BusinessCoachInsight, id=pk, store__user=request.user)
        insight.is_read = True
        insight.read_at = timezone.now()
        insight.save(update_fields=['is_read', 'read_at'])
        return Response({'status': 'marked_read'})


@extend_schema(exclude=True)
class CoachInsightDismissView(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, pk):
        insight = get_object_or_404(BusinessCoachInsight, id=pk, store__user=request.user)
        insight.is_dismissed = True
        insight.save(update_fields=['is_dismissed'])
        return Response({'status': 'dismissed'})


@extend_schema(exclude=True)
class GenerateCoachInsightsView(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        from ai_intelligence.services.business_coach import get_business_coach_service
        if request.user.role != 'seller':
            return Response({'error': 'Seller access required'}, status=403)
        store = getattr(request.user, 'store', None)
        if not store:
            return Response({'error': 'No store found'}, status=404)
        coach = get_business_coach_service()
        insights = coach.generate_insights_for_store(store)
        created = []
        for insight in insights:
            obj = BusinessCoachInsight.objects.create(store=store, computed_at=timezone.now(), **insight)
            created.append(BusinessCoachInsightSerializer(obj).data)
        return Response({'insights': created})


# ── Personal Shopping Assistant ──

class ShoppingInsightsView(generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = PersonalShoppingInsightSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return PersonalShoppingInsight.objects.none()
        return PersonalShoppingInsight.objects.filter(
            user=self.request.user, is_dismissed=False
        ).order_by('-computed_at')[:20]


@extend_schema(exclude=True)
class ShoppingInsightReadView(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, pk):
        insight = generics.get_object_or_404(PersonalShoppingInsight, id=pk, user=request.user)
        insight.is_read = True
        insight.save(update_fields=['is_read'])
        return Response({'status': 'read'})


# ── Predictions ──

@extend_schema(exclude=True)
class DemandPredictionView(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, product_id):
        from products.models import Product
        from ai_intelligence.services.prediction_engine import get_prediction_engine
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=404)
        engine = get_prediction_engine()
        result = engine.predict_demand(product)
        return Response(result)


@extend_schema(exclude=True)
class PriceRecommendationView(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, product_id):
        from products.models import Product
        from ai_intelligence.services.prediction_engine import get_prediction_engine
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=404)
        engine = get_prediction_engine()
        result = engine.recommend_price(product)
        return Response(result)


@extend_schema(exclude=True)
class SalesForecastView(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, store_id):
        from stores.models import Store
        from ai_intelligence.services.prediction_engine import get_prediction_engine
        try:
            store = Store.objects.get(id=store_id)
        except Store.DoesNotExist:
            return Response({'error': 'Store not found'}, status=404)
        engine = get_prediction_engine()
        result = engine.forecast_sales(store)
        return Response(result)


# ── Segmentation ──

@extend_schema(exclude=True)
class MySegmentsView(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        from ai_intelligence.services.segmentation import get_segmentation_engine
        engine = get_segmentation_engine()
        segment_name = engine.segment_user(request.user)
        characteristics = engine.get_segment_characteristics(segment_name)
        return Response({
            'segment': segment_name,
            'characteristics': characteristics,
        })


class SegmentListView(generics.ListAPIView):
    queryset = CustomerSegment.objects.filter(is_active=True)
    serializer_class = CustomerSegmentSerializer
    permission_classes = (permissions.IsAuthenticated,)


# ── Gamification ──

@extend_schema(exclude=True)
class GamificationProfileView(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        from ai_intelligence.services.gamification import get_gamification_engine
        profile, _ = GamificationProfile.objects.get_or_create(user=request.user)
        engine = get_gamification_engine()
        challenges = engine.get_or_create_daily_challenges(request.user)
        return Response({
            'profile': GamificationProfileSerializer(profile).data,
            'daily_challenges': challenges,
        })


class UserChallengesView(generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = UserChallengeProgressSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return UserChallengeProgress.objects.none()
        return UserChallengeProgress.objects.filter(
            user=self.request.user
        ).select_related('challenge').order_by('-is_completed', '-updated_at')[:20]


# ── Learning Engine ──

class AIModelRegistryView(generics.ListAPIView):
    queryset = AIModelRegistry.objects.filter(is_active=True)
    serializer_class = AIModelRegistrySerializer
    permission_classes = (permissions.IsAdminUser,)


class ExperimentResultView(generics.ListAPIView):
    queryset = ExperimentResult.objects.all().order_by('-created_at')
    serializer_class = ExperimentResultSerializer
    permission_classes = (permissions.IsAdminUser,)


# ── Dashboards ──

@extend_schema(exclude=True)
class ExecutiveDashboardView(views.APIView):
    permission_classes = (permissions.IsAdminUser,)

    def get(self, request):
        from django.contrib.auth import get_user_model
        from orders.models import Order
        from engagement.models import UserBehaviorProfile
        User = get_user_model()

        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)

        # Marketplace health
        health = MarketplaceHealthSnapshot.objects.order_by('-snapshot_time').first()

        # User stats
        total_users = User.objects.filter(is_active=True).count()
        total_buyers = User.objects.filter(is_active=True, role='buyer').count()
        total_sellers = User.objects.filter(is_active=True, role='seller').count()
        new_users_30d = User.objects.filter(date_joined__gte=thirty_days_ago).count()

        # Revenue
        revenue_30d = Order.objects.filter(
            created_at__gte=thirty_days_ago,
            order_status__in=['paid', 'completed', 'shipped']
        ).aggregate(total=Sum('total_price'))['total'] or 0

        # Engagement
        avg_engagement = UserBehaviorProfile.objects.aggregate(
            avg=Avg('engagement_score'))['avg'] or 0
        at_risk = UserBehaviorProfile.objects.filter(risk_level='at_risk').count()

        # Top coach insights
        top_insights = BusinessCoachInsight.objects.filter(
            is_dismissed=False
        ).select_related('store').order_by('-priority', '-created_at')[:5]

        return Response({
            'marketplace_health': MarketplaceHealthSnapshotSerializer(health).data if health else {},
            'growth_metrics': {
                'total_users': total_users,
                'total_buyers': total_buyers,
                'total_sellers': total_sellers,
                'new_users_30d': new_users_30d,
                'revenue_30d': str(revenue_30d),
                'avg_engagement': round(float(avg_engagement), 2),
            },
            'risk_metrics': {
                'at_risk_users': at_risk,
                'churn_rate': round((at_risk / max(total_users, 1)) * 100, 2),
            },
            'top_insights': BusinessCoachInsightSerializer(top_insights, many=True).data,
        })


@extend_schema(exclude=True)
class SellerDashboardView(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        from orders.models import Order
        from engagement.models import UserBehaviorProfile

        if request.user.role != 'seller':
            return Response({'error': 'Seller access required'}, status=403)

        store = getattr(request.user, 'store', None)
        if not store:
            return Response({'error': 'No store found'}, status=404)

        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)

        # Store performance
        orders_30d = Order.objects.filter(store=store, created_at__gte=thirty_days_ago).count()
        revenue_30d = Order.objects.filter(
            store=store, created_at__gte=thirty_days_ago,
            order_status__in=['paid', 'completed', 'shipped']
        ).aggregate(total=Sum('total_price'))['total'] or 0

        # Digital Twin
        twin, _ = DigitalTwin.objects.get_or_create(user=request.user)

        # Coach insights
        insights = BusinessCoachInsight.objects.filter(
            store=store, is_dismissed=False
        ).order_by('-priority', '-created_at')[:10]

        # Products
        product_count = store.products.filter(is_active=True).count()
        oos_count = store.products.filter(is_active=True, stock=0).count()

        return Response({
            'store_health': {
                'store_health_score': twin.store_health_score,
                'inventory_health_score': twin.inventory_health_score,
                'product_opportunity_score': twin.product_opportunity_score,
            },
            'performance_metrics': {
                'orders_30d': orders_30d,
                'revenue_30d': str(revenue_30d),
                'total_products': product_count,
                'out_of_stock': oos_count,
                'seller_performance_score': twin.seller_performance_score,
            },
            'coach_insights': BusinessCoachInsightSerializer(insights, many=True).data,
            'digital_twin': DigitalTwinSerializer(twin).data,
        })


@extend_schema(exclude=True)
class BuyerDashboardView(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        from engagement.models import UserBehaviorProfile
        from engagement.services.scoring_engine import get_scoring_engine
        from ai_intelligence.services.segmentation import get_segmentation_engine
        from ai_intelligence.services.gamification import get_gamification_engine

        profile, _ = UserBehaviorProfile.objects.get_or_create(user=request.user)
        twin, _ = DigitalTwin.objects.get_or_create(user=request.user)
        gamification, _ = GamificationProfile.objects.get_or_create(user=request.user)

        seg_engine = get_segmentation_engine()
        segment_name = seg_engine.segment_user(request.user)
        seg_chars = seg_engine.get_segment_characteristics(segment_name)

        game_engine = get_gamification_engine()
        challenges = game_engine.get_or_create_daily_challenges(request.user)

        shopping_insights = PersonalShoppingInsight.objects.filter(
            user=request.user, is_dismissed=False
        ).order_by('-computed_at')[:5]

        return Response({
            'digital_twin': DigitalTwinSerializer(twin).data,
            'gamification': {
                'profile': GamificationProfileSerializer(gamification).data,
                'daily_challenges': challenges,
            },
            'segment': {
                'name': segment_name,
                'characteristics': seg_chars,
            },
            'shopping_insights': PersonalShoppingInsightSerializer(shopping_insights, many=True).data,
            'engagement_profile': {
                'engagement_score': profile.engagement_score,
                'retention_score': profile.retention_score,
                'churn_risk_score': profile.churn_risk_score,
                'loyalty_score': profile.loyalty_score,
                'notification_fatigue_score': profile.notification_fatigue_score,
            },
        })
