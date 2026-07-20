"""
Serializers for AI Intelligence Platform APIs.
"""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.openapi import OpenApiTypes

from ai_intelligence.models import (
    DigitalTwin, MarketplaceHealthSnapshot, DemandPrediction,
    PricingRecommendation, SalesForecast, CustomerSegment,
    UserSegmentAssignment, GamificationProfile, Challenge,
    UserChallengeProgress, BusinessCoachInsight, PersonalShoppingInsight,
    AIModelRegistry, ExperimentResult,
)


class DigitalTwinSerializer(serializers.ModelSerializer):
    class Meta:
        model = DigitalTwin
        exclude = ('user', 'twin_version', 'created_at')
        read_only_fields = [f.name for f in DigitalTwin._meta.fields if f.name != 'id']


class MarketplaceHealthSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketplaceHealthSnapshot
        fields = '__all__'
        read_only_fields = ('created_at',)


class DemandPredictionSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.product_name', read_only=True)
    store_name = serializers.CharField(source='store.store_name', read_only=True)

    class Meta:
        model = DemandPrediction
        fields = '__all__'
        read_only_fields = ('created_at',)


class PricingRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PricingRecommendation
        fields = '__all__'
        read_only_fields = ('created_at',)


class CustomerSegmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerSegment
        fields = '__all__'


class GamificationProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = GamificationProfile
        exclude = ('user', 'created_at')
        read_only_fields = [f.name for f in GamificationProfile._meta.fields if f.name != 'id']


class ChallengeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Challenge
        fields = '__all__'


class UserChallengeProgressSerializer(serializers.ModelSerializer):
    challenge_name = serializers.CharField(source='challenge.name', read_only=True)
    progress_pct = serializers.SerializerMethodField()

    class Meta:
        model = UserChallengeProgress
        fields = '__all__'
        read_only_fields = ('started_at', 'updated_at')

    @extend_schema_field(OpenApiTypes.STR)
    def get_progress_pct(self, obj):
        return round((obj.current_value / max(obj.target_value, 1)) * 100, 1)


class BusinessCoachInsightSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.store_name', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = BusinessCoachInsight
        fields = '__all__'
        read_only_fields = ('created_at', 'computed_at')


class PersonalShoppingInsightSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonalShoppingInsight
        fields = '__all__'
        read_only_fields = ('created_at',)


class AIModelRegistrySerializer(serializers.ModelSerializer):
    class Meta:
        model = AIModelRegistry
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class ExperimentResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExperimentResult
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class ExecutiveDashboardSerializer(serializers.Serializer):
    marketplace_health = serializers.DictField()
    growth_metrics = serializers.DictField()
    risk_metrics = serializers.DictField()
    top_insights = serializers.ListField()


class SellerDashboardSerializer(serializers.Serializer):
    store_health = serializers.DictField()
    performance_metrics = serializers.DictField()
    coach_insights = serializers.ListField()
    recommendations = serializers.ListField()


class BuyerDashboardSerializer(serializers.Serializer):
    digital_twin = serializers.DictField()
    gamification = serializers.DictField()
    shopping_insights = serializers.ListField()
    recommendations = serializers.ListField()
