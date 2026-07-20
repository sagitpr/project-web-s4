"""
AI Intelligence Platform Models for Warungio Marketplace.

Model Categories:
1. AI Digital Twin — Predictive user model with CLV, growth, interest scores
2. Marketplace Health — Platform-wide health monitoring
3. Business Coach — Seller-specific intelligence and coaching
4. Prediction Engine — Demand, revenue, inventory, sales forecasts
5. Customer Segmentation — RFM + behavioral persona clusters
6. Habit & Gamification — Challenges, streaks, badges, behavioral loops
7. Learning Engine — Model registry, experiment tracking, self-improvement
"""

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal


# ═══════════════════════════════════════════════════════════════
# 1. AI DIGITAL TWIN
# ═══════════════════════════════════════════════════════════════

class DigitalTwin(models.Model):
    """
    AI Digital Twin — continuously updated predictive model of each user.
    Extends UserBehaviorProfile with forward-looking predictions.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='digital_twin', verbose_name='Pengguna'
    )

    # ── Identity & Archetype ──
    buyer_persona = models.CharField(max_length=50, blank=True, default='', verbose_name='Persona Pembeli')
    seller_archetype = models.CharField(max_length=50, blank=True, default='', verbose_name='Arketipe Penjual')
    behavioral_quirks = models.JSONField(default=list, blank=True, verbose_name='Pola Unik')
    emotional_state = models.CharField(max_length=30, blank=True, default='neutral',
        choices=[('delighted','Delighted'),('satisfied','Satisfied'),('neutral','Neutral'),
                 ('frustrated','Frustrated'),('at_risk','At Risk')],
        verbose_name='Kondisi Emosional')

    # ── Predictive Scores ──
    customer_lifetime_value = models.DecimalField(max_digits=14, decimal_places=2, default=0,
        verbose_name='Predicted CLV (Rp)')
    clv_confidence = models.FloatField(default=0.0, verbose_name='CLV Confidence (0-1)')
    predicted_next_purchase_days = models.IntegerField(default=0, verbose_name='Prediksi Pembelian Berikut (hari)')
    predicted_next_purchase_at = models.DateTimeField(null=True, blank=True)
    predicted_next_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0,
        verbose_name='Prediksi Nilai Pesanan Berikut')
    repeat_purchase_probability = models.FloatField(default=0.0, verbose_name='Probabilitas Repeat Purchase')
    growth_score = models.FloatField(default=0.0, validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Growth Score')
    buyer_interest_score = models.FloatField(default=0.0, validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Buyer Interest Score')

    # ── Trust & Reputation ──
    trust_score = models.FloatField(default=50.0, validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Trust Score')
    reputation_score = models.FloatField(default=50.0, validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Reputation Score')
    seller_performance_score = models.FloatField(default=0.0, validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Seller Performance Score')

    # ── Store Health ──
    store_health_score = models.FloatField(default=0.0, validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Store Health Score')
    inventory_health_score = models.FloatField(default=0.0, validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Inventory Health Score')
    product_opportunity_score = models.FloatField(default=0.0, validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Product Opportunity Score')

    # ── Revenue & Growth ──
    predicted_revenue_7d = models.DecimalField(max_digits=14, decimal_places=2, default=0,
        verbose_name='Predicted Revenue 7d')
    predicted_revenue_30d = models.DecimalField(max_digits=14, decimal_places=2, default=0,
        verbose_name='Predicted Revenue 30d')
    predicted_revenue_90d = models.DecimalField(max_digits=14, decimal_places=2, default=0,
        verbose_name='Predicted Revenue 90d')
    revenue_prediction_confidence = models.FloatField(default=0.0, verbose_name='Revenue Prediction Confidence')

    # ── Emotion & Sentiment ──
    sentiment_trend = models.CharField(max_length=20, blank=True, default='neutral',
        choices=[('improving','Improving'),('stable','Stable'),('declining','Declining'),('neutral','Neutral')],
        verbose_name='Sentiment Trend')
    last_sentiment_score = models.FloatField(default=0.0, verbose_name='Last Sentiment Score (-1 to 1)')
    emotion_history = models.JSONField(default=list, blank=True, verbose_name='Emotion History')

    # ── Geo & Community ──
    geo_affinity_zone = models.CharField(max_length=100, blank=True, default='', verbose_name='Geo Affinity Zone')
    community_engagement_score = models.FloatField(default=0.0, verbose_name='Community Engagement')
    hyperlocal_affinity = models.CharField(max_length=100, blank=True, default='', verbose_name='Hyperlocal Affinity')

    # ── Twin Metadata ──
    twin_version = models.IntegerField(default=1)
    accuracy_score = models.FloatField(default=0.0, verbose_name='Digital Twin Accuracy')
    last_prediction_at = models.DateTimeField(null=True, blank=True)
    computed_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ai_digital_twins'
        verbose_name = 'AI Digital Twin'
        verbose_name_plural = 'AI Digital Twins'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['buyer_persona']),
            models.Index(fields=['customer_lifetime_value']),
            models.Index(fields=['predicted_next_purchase_at']),
            models.Index(fields=['growth_score']),
            models.Index(fields=['store_health_score']),
        ]

    def __str__(self):
        return f'DigitalTwin: {self.user.email} (CLV={self.customer_lifetime_value}, persona={self.buyer_persona})'


# ═══════════════════════════════════════════════════════════════
# 2. MARKETPLACE HEALTH
# ═══════════════════════════════════════════════════════════════

class MarketplaceHealthSnapshot(models.Model):
    """
    Periodic snapshot of marketplace-wide health metrics.
    Captures the pulse of the entire Warungio ecosystem.
    """
    snapshot_time = models.DateTimeField(db_index=True, verbose_name='Waktu Snapshot')

    # ── Scale Metrics ──
    total_active_users = models.IntegerField(default=0)
    total_active_sellers = models.IntegerField(default=0)
    total_active_buyers = models.IntegerField(default=0)
    total_active_stores = models.IntegerField(default=0)
    total_listings = models.IntegerField(default=0)

    # ── Transaction Metrics ──
    orders_last_24h = models.IntegerField(default=0)
    orders_last_7d = models.IntegerField(default=0)
    orders_last_30d = models.IntegerField(default=0)
    gmv_last_24h = models.DecimalField(max_digits=16, decimal_places=2, default=0, verbose_name='GMV 24h')
    gmv_last_7d = models.DecimalField(max_digits=16, decimal_places=2, default=0, verbose_name='GMV 7d')
    gmv_last_30d = models.DecimalField(max_digits=16, decimal_places=2, default=0, verbose_name='GMV 30d')
    avg_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    conversion_rate = models.FloatField(default=0.0, verbose_name='Conversion Rate')

    # ── Engagement Metrics ──
    avg_engagement_score = models.FloatField(default=0.0)
    avg_retention_score = models.FloatField(default=0.0)
    avg_churn_risk = models.FloatField(default=0.0)
    total_at_risk_users = models.IntegerField(default=0)
    total_churned_users = models.IntegerField(default=0)
    new_registrations_24h = models.IntegerField(default=0)
    re_engagements_24h = models.IntegerField(default=0)

    # ── Delivery Metrics ──
    delivery_success_rate = models.FloatField(default=0.0)
    avg_delivery_time_minutes = models.FloatField(default=0.0)
    on_time_delivery_pct = models.FloatField(default=0.0)

    # ── Financial Health ──
    total_wallet_balance = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    pending_payouts = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    refund_rate = models.FloatField(default=0.0)

    # ── AI Performance ──
    total_ai_scans_24h = models.IntegerField(default=0)
    total_recommendations_served = models.IntegerField(default=0)
    recommendation_click_rate = models.FloatField(default=0.0)
    ai_chat_resolution_rate = models.FloatField(default=0.0)

    # ── Composite Health Score ──
    marketplace_health_score = models.FloatField(default=0.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Marketplace Health Score')
    growth_index = models.FloatField(default=0.0, verbose_name='Growth Index')
    stability_index = models.FloatField(default=0.0, verbose_name='Stability Index')

    # ── Trend Indicators ──
    trend_direction = models.CharField(max_length=20, blank=True, default='stable',
        choices=[('growing','Growing'),('stable','Stable'),('declining','Declining'),('critical','Critical')],
        verbose_name='Marketplace Trend')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ai_marketplace_health'
        verbose_name = 'Marketplace Health Snapshot'
        verbose_name_plural = 'Marketplace Health Snapshots'
        indexes = [
            models.Index(fields=['snapshot_time']),
            models.Index(fields=['marketplace_health_score']),
        ]
        ordering = ['-snapshot_time']

    def __str__(self):
        return f'MarketplaceHealth: {self.snapshot_time} (score={self.marketplace_health_score:.1f}, trend={self.trend_direction})'


# ═══════════════════════════════════════════════════════════════
# 3. PREDICTION ENGINE
# ═══════════════════════════════════════════════════════════════

class DemandPrediction(models.Model):
    """
    AI-powered demand predictions for products.
    Uses historical sales, seasonality, trends to forecast demand.
    """
    product = models.ForeignKey(
        'products.Product', on_delete=models.CASCADE,
        related_name='demand_predictions', verbose_name='Produk'
    )
    store = models.ForeignKey(
        'stores.Store', on_delete=models.CASCADE,
        related_name='demand_predictions', verbose_name='Toko'
    )

    # ── Forecast Period ──
    forecast_date = models.DateField(verbose_name='Tanggal Forecast')
    forecast_period = models.CharField(max_length=20,
        choices=[('daily','Daily'),('weekly','Weekly'),('monthly','Monthly')],
        default='daily', verbose_name='Periode Forecast')

    # ── Demand Forecast ──
    predicted_demand = models.IntegerField(default=0, verbose_name='Predicted Demand (units)')
    predicted_demand_low = models.IntegerField(default=0, verbose_name='Lower Bound')
    predicted_demand_high = models.IntegerField(default=0, verbose_name='Upper Bound')
    confidence_score = models.FloatField(default=0.0, verbose_name='Confidence (0-1)')

    # ── Seasonality ──
    seasonal_factor = models.FloatField(default=1.0, verbose_name='Seasonal Factor')
    day_of_week_factor = models.FloatField(default=1.0, verbose_name='Day of Week Factor')
    holiday_factor = models.FloatField(default=1.0, verbose_name='Holiday Factor')
    weather_factor = models.FloatField(default=1.0, verbose_name='Weather Factor')

    # ── Price Sensitivity ──
    price_elasticity = models.FloatField(default=0.0, verbose_name='Price Elasticity')
    optimal_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name='Optimal Price (Rp)')
    predicted_revenue = models.DecimalField(max_digits=14, decimal_places=2, default=0,
        verbose_name='Predicted Revenue')

    # ── Inventory Recommendation ──
    recommended_stock = models.IntegerField(default=0, verbose_name='Recommended Stock')
    restock_urgency = models.CharField(max_length=20, blank=True, default='normal',
        choices=[('critical','Critical'),('high','High'),('normal','Normal'),('low','Low')],
        verbose_name='Restock Urgency')
    days_until_stockout = models.IntegerField(default=30, verbose_name='Days Until Stockout')

    # ── Metadata ──
    model_version = models.CharField(max_length=50, blank=True, default='')
    features_used = models.JSONField(default=list, blank=True)
    prediction_errors = models.JSONField(default=list, blank=True)
    computed_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ai_demand_predictions'
        verbose_name = 'Demand Prediction'
        verbose_name_plural = 'Demand Predictions'
        indexes = [
            models.Index(fields=['product', 'forecast_date']),
            models.Index(fields=['store', 'forecast_date']),
            models.Index(fields=['forecast_date']),
            models.Index(fields=['restock_urgency']),
        ]
        unique_together = [['product', 'forecast_date', 'forecast_period']]

    def __str__(self):
        return f'DemandPred: {self.product.product_name} on {self.forecast_date} (demand={self.predicted_demand})'


class PricingRecommendation(models.Model):
    """
    AI-powered pricing recommendations.
    Suggests optimal prices based on demand, competition, seasonality.
    """
    product = models.ForeignKey(
        'products.Product', on_delete=models.CASCADE,
        related_name='pricing_recommendations', verbose_name='Produk'
    )
    store = models.ForeignKey(
        'stores.Store', on_delete=models.CASCADE,
        related_name='pricing_recommendations', verbose_name='Toko'
    )

    current_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Current Price')
    recommended_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Recommended Price')
    min_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Minimum Recommended Price')
    max_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Maximum Recommended Price')

    price_change_pct = models.FloatField(default=0.0, verbose_name='Price Change %')
    expected_demand_change = models.FloatField(default=0.0, verbose_name='Expected Demand Change %')
    expected_revenue_change = models.FloatField(default=0.0, verbose_name='Expected Revenue Change %')
    confidence_score = models.FloatField(default=0.0, verbose_name='Confidence')

    strategy = models.CharField(max_length=50, blank=True, default='market',
        choices=[('premium','Premium'),('competitive','Competitive'),('penetration','Penetration'),
                 ('economy','Economy'),('market','Market Follow'),('dynamic','Dynamic')],
        verbose_name='Pricing Strategy')
    reasoning = models.TextField(blank=True, default='', verbose_name='AI Reasoning')

    is_applied = models.BooleanField(default=False, verbose_name='Price Applied?')
    applied_at = models.DateTimeField(null=True, blank=True)
    result_impact = models.JSONField(default=dict, blank=True, verbose_name='Result Impact')

    model_version = models.CharField(max_length=50, blank=True, default='')
    computed_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ai_pricing_recommendations'
        verbose_name = 'Pricing Recommendation'
        verbose_name_plural = 'Pricing Recommendations'
        indexes = [
            models.Index(fields=['product', 'computed_at']),
            models.Index(fields=['store', 'is_applied']),
        ]

    def __str__(self):
        return f'PriceRec: {self.product.product_name} ({self.current_price} → {self.recommended_price})'


class SalesForecast(models.Model):
    """
    Aggregate sales forecasting for stores and marketplace.
    """
    store = models.ForeignKey(
        'stores.Store', on_delete=models.CASCADE,
        null=True, blank=True, related_name='sales_forecasts',
        verbose_name='Toko (null=marketplace)'
    )
    forecast_date = models.DateField(verbose_name='Tanggal Forecast')
    period = models.CharField(max_length=20,
        choices=[('daily','Daily'),('weekly','Weekly'),('monthly','Monthly'),('quarterly','Quarterly')],
        default='weekly')

    predicted_orders = models.IntegerField(default=0)
    predicted_revenue = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    predicted_gmv = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    confidence_lower = models.DecimalField(max_digits=16, decimal_places=2, default=0,
        verbose_name='Lower Bound Revenue')
    confidence_upper = models.DecimalField(max_digits=16, decimal_places=2, default=0,
        verbose_name='Upper Bound Revenue')
    confidence_score = models.FloatField(default=0.0)

    # Growth vs prior period
    growth_vs_prior_pct = models.FloatField(default=0.0, verbose_name='Growth vs Prior Period %')

    actual_orders = models.IntegerField(null=True, blank=True)
    actual_revenue = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    forecast_error_pct = models.FloatField(null=True, blank=True)

    model_version = models.CharField(max_length=50, blank=True, default='')
    computed_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ai_sales_forecasts'
        verbose_name = 'Sales Forecast'
        verbose_name_plural = 'Sales Forecasts'
        indexes = [
            models.Index(fields=['store', 'forecast_date']),
            models.Index(fields=['forecast_date', 'period']),
        ]
        unique_together = [['store', 'forecast_date', 'period']]

    def __str__(self):
        return f'SalesForecast: {"Marketplace" if not self.store else self.store.store_name} on {self.forecast_date}'


# ═══════════════════════════════════════════════════════════════
# 4. CUSTOMER SEGMENTATION
# ═══════════════════════════════════════════════════════════════

class CustomerSegment(models.Model):
    """
    Customer segmentation configuration and results.
    Defines segment types and their characteristics.
    """
    SEGMENT_TYPES = [
        ('rfm', 'RFM Segment'),
        ('behavioral', 'Behavioral Cluster'),
        ('persona', 'AI Persona'),
        ('value', 'Value Segment'),
        ('lifecycle', 'Lifecycle Stage'),
    ]

    name = models.CharField(max_length=100, verbose_name='Nama Segmen')
    segment_type = models.CharField(max_length=30, choices=SEGMENT_TYPES, verbose_name='Tipe Segmen')
    description = models.TextField(blank=True, default='', verbose_name='Deskripsi')
    criteria = models.JSONField(default=dict, blank=True, verbose_name='Kriteria')
    color = models.CharField(max_length=20, blank=True, default='#6C5CE7', verbose_name='Warna')
    icon = models.CharField(max_length=100, blank=True, default='', verbose_name='Ikon')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ai_customer_segments'
        verbose_name = 'Segmen Pelanggan'
        verbose_name_plural = 'Segmen Pelanggan'

    def __str__(self):
        return f'{self.name} ({self.get_segment_type_display()})'


class UserSegmentAssignment(models.Model):
    """
    Tracks which segments each user belongs to.
    Users can belong to multiple segments.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='segment_assignments', verbose_name='Pengguna'
    )
    segment = models.ForeignKey(
        CustomerSegment, on_delete=models.CASCADE,
        related_name='user_assignments', verbose_name='Segmen'
    )
    score = models.FloatField(default=0.0, verbose_name='Segment Affinity Score')
    is_primary = models.BooleanField(default=False, verbose_name='Segmen Utama')
    assigned_by = models.CharField(max_length=50, blank=True, default='ai', verbose_name='Ditugaskan Oleh')
    assigned_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_user_segments'
        verbose_name = 'Segment Assignment'
        verbose_name_plural = 'Segment Assignments'
        unique_together = [['user', 'segment']]
        indexes = [
            models.Index(fields=['user', 'is_primary']),
            models.Index(fields=['segment', 'score']),
        ]

    def __str__(self):
        return f'{self.user.email} → {self.segment.name} (score={self.score:.2f})'


# ═══════════════════════════════════════════════════════════════
# 5. HABIT & GAMIFICATION
# ═══════════════════════════════════════════════════════════════

class GamificationProfile(models.Model):
    """
    Per-user gamification profile tracking levels, XP, and progress.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='gamification_profile', verbose_name='Pengguna'
    )

    # ── Leveling ──
    level = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    xp_points = models.IntegerField(default=0, verbose_name='Total XP')
    xp_to_next_level = models.IntegerField(default=100, verbose_name='XP to Next Level')
    total_xp_earned = models.IntegerField(default=0, verbose_name='Total XP Earned')

    # ── Streaks ──
    current_streak_days = models.IntegerField(default=0, verbose_name='Current Streak (days)')
    longest_streak_days = models.IntegerField(default=0, verbose_name='Longest Streak (days)')
    streak_multiplier = models.FloatField(default=1.0, verbose_name='Streak XP Multiplier')
    last_streak_activity = models.DateTimeField(null=True, blank=True)

    # ── Badges ──
    badges_earned = models.JSONField(default=list, blank=True, verbose_name='Badges Earned')
    total_badges = models.IntegerField(default=0, verbose_name='Total Badges')
    rare_badges = models.IntegerField(default=0, verbose_name='Rare Badges')

    # ── Challenges ──
    active_challenges = models.JSONField(default=list, blank=True, verbose_name='Active Challenges')
    completed_challenges = models.IntegerField(default=0, verbose_name='Completed Challenges')
    challenge_success_rate = models.FloatField(default=0.0, verbose_name='Challenge Success Rate')

    # ── Rewards ──
    rewards_unlocked = models.JSONField(default=list, blank=True, verbose_name='Rewards Unlocked')
    next_reward_at_xp = models.IntegerField(default=500, verbose_name='Next Reward at XP')
    reward_multiplier = models.FloatField(default=1.0, verbose_name='Reward Multiplier')

    # ── Behavioral Loop State ──
    habit_loop_phase = models.CharField(max_length=30, blank=True, default='discovery',
        choices=[('discovery','Discovery'),('trigger','Trigger'),('action','Action'),
                 ('reward','Reward'),('investment','Investment'),('maintenance','Maintenance')],
        verbose_name='Habit Loop Phase')
    loop_strength = models.FloatField(default=0.0, verbose_name='Habit Loop Strength (0-1)')
    days_in_phase = models.IntegerField(default=0, verbose_name='Days in Current Phase')

    computed_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ai_gamification_profiles'
        verbose_name = 'Profil Gamifikasi'
        verbose_name_plural = 'Profil Gamifikasi'
        indexes = [
            models.Index(fields=['level']),
            models.Index(fields=['current_streak_days']),
            models.Index(fields=['habit_loop_phase']),
        ]

    def __str__(self):
        return f'GameProfile: {self.user.email} (Lv.{self.level}, {self.xp_points}XP, streak={self.current_streak_days}d)'


class Challenge(models.Model):
    """
    Gamification challenges that users can participate in.
    """
    CHALLENGE_TYPES = [
        ('daily','Daily Challenge'),
        ('weekly','Weekly Challenge'),
        ('monthly','Monthly Challenge'),
        ('milestone','Milestone Challenge'),
        ('social','Social Challenge'),
        ('seasonal','Seasonal Event'),
    ]

    DIFFICULTY_CHOICES = [
        ('easy','Easy'),('medium','Medium'),('hard','Hard'),('legendary','Legendary'),
    ]

    name = models.CharField(max_length=200, verbose_name='Nama Challenge')
    description = models.TextField(verbose_name='Deskripsi')
    challenge_type = models.CharField(max_length=20, choices=CHALLENGE_TYPES, verbose_name='Tipe')
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='medium')

    # Requirements
    requirement_type = models.CharField(max_length=50, verbose_name='Requirement Type',
        help_text='e.g., orders_count, total_spend, login_streak, reviews_written, ai_scans')
    requirement_value = models.IntegerField(default=1, verbose_name='Target Value')
    requirement_logic = models.CharField(max_length=20, default='gte',
        choices=[('gte','≥'),('lte','≤'),('eq','=')], verbose_name='Logic')

    # Rewards
    xp_reward = models.IntegerField(default=50, verbose_name='XP Reward')
    badge_reward = models.CharField(max_length=100, blank=True, default='', verbose_name='Badge Reward')
    coin_reward = models.IntegerField(default=0, verbose_name='Coin Reward')
    coupon_code = models.CharField(max_length=50, blank=True, default='', verbose_name='Coupon Code')

    # Targeting
    target_role = models.CharField(max_length=20, blank=True, default='',
        choices=[('buyer','Buyer'),('seller','Seller'),('','All')])
    target_segment = models.ForeignKey(
        CustomerSegment, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='challenges', verbose_name='Target Segment'
    )

    # Schedule
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    is_recurring = models.BooleanField(default=False)
    recurrence_pattern = models.CharField(max_length=50, blank=True, default='')

    # Status
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    max_participants = models.IntegerField(default=0, verbose_name='0=unlimited')
    current_participants = models.IntegerField(default=0)

    # AI Generated
    ai_generated = models.BooleanField(default=False)
    ai_prompt_used = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_challenges'
        verbose_name = 'Challenge'
        verbose_name_plural = 'Challenges'
        indexes = [
            models.Index(fields=['challenge_type', 'is_active']),
            models.Index(fields=['difficulty']),
            models.Index(fields=['start_date', 'end_date']),
        ]

    def __str__(self):
        return f'{self.name} ({self.get_difficulty_display()}, {self.xp_reward}XP)'


class UserChallengeProgress(models.Model):
    """
    Tracks each user's progress on challenges.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='challenge_progress', verbose_name='Pengguna'
    )
    challenge = models.ForeignKey(
        Challenge, on_delete=models.CASCADE,
        related_name='user_progress', verbose_name='Challenge'
    )
    current_value = models.IntegerField(default=0, verbose_name='Current Progress')
    target_value = models.IntegerField(default=1, verbose_name='Target')
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    reward_claimed = models.BooleanField(default=False)
    reward_claimed_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_challenge_progress'
        verbose_name = 'Challenge Progress'
        verbose_name_plural = 'Challenge Progress'
        unique_together = [['user', 'challenge']]
        indexes = [
            models.Index(fields=['user', 'is_completed']),
            models.Index(fields=['challenge', 'is_completed']),
        ]

    def __str__(self):
        return f'{self.user.email} → {self.challenge.name}: {self.current_value}/{self.target_value}'


# ═══════════════════════════════════════════════════════════════
# 6. BUSINESS COACH
# ═══════════════════════════════════════════════════════════════

class BusinessCoachInsight(models.Model):
    """
    AI-generated business coaching insights for sellers.
    Proactively identifies opportunities and risks.
    """
    INSIGHT_CATEGORIES = [
        ('growth','Growth Opportunity'),
        ('risk','Risk Alert'),
        ('optimization','Optimization Suggestion'),
        ('inventory','Inventory Insight'),
        ('pricing','Pricing Insight'),
        ('marketing','Marketing Insight'),
        ('customer','Customer Insight'),
        ('product','Product Insight'),
        ('revenue','Revenue Insight'),
        ('operation','Operational Insight'),
    ]

    PRIORITY_CHOICES = [
        (0, 'Info'), (1, 'Low'), (2, 'Medium'), (3, 'High'), (4, 'Critical'),
    ]

    store = models.ForeignKey(
        'stores.Store', on_delete=models.CASCADE,
        related_name='coach_insights', verbose_name='Toko'
    )
    category = models.CharField(max_length=30, choices=INSIGHT_CATEGORIES, verbose_name='Kategori')
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=1, verbose_name='Prioritas')

    title = models.CharField(max_length=255, verbose_name='Judul Insight')
    description = models.TextField(verbose_name='Deskripsi')
    recommendation = models.TextField(verbose_name='Rekomendasi')
    expected_impact = models.CharField(max_length=255, blank=True, default='', verbose_name='Dampak yang Diharapkan')

    # Supporting data
    supporting_data = models.JSONField(default=dict, blank=True, verbose_name='Data Pendukung')
    metric_before = models.FloatField(null=True, blank=True, verbose_name='Metric Before')
    metric_after = models.FloatField(null=True, blank=True, verbose_name='Metric After (optional)')

    # AI metadata
    ai_generated = models.BooleanField(default=True)
    ai_reasoning = models.TextField(blank=True, default='', verbose_name='AI Reasoning')
    model_version = models.CharField(max_length=50, blank=True, default='')

    # Status
    is_read = models.BooleanField(default=False)
    is_dismissed = models.BooleanField(default=False)
    is_actioned = models.BooleanField(default=False)
    actioned_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    computed_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ai_coach_insights'
        verbose_name = 'Business Coach Insight'
        verbose_name_plural = 'Business Coach Insights'
        indexes = [
            models.Index(fields=['store', 'priority']),
            models.Index(fields=['store', 'category']),
            models.Index(fields=['store', 'is_read']),
            models.Index(fields=['computed_at']),
        ]
        ordering = ['-priority', '-created_at']

    def __str__(self):
        return f'CoachInsight: {self.title} ({self.get_category_display()}, priority={self.priority})'


class PersonalShoppingInsight(models.Model):
    """
    AI-generated personal shopping assistant insights for buyers.
    """
    INSIGHT_TYPES = [
        ('recommendation','Product Recommendation'),
        ('deal_alert','Deal Alert'),
        ('restock_alert','Restock Alert'),
        ('price_drop','Price Drop Alert'),
        ('cart_reminder','Cart Reminder'),
        ('wishlist_alert','Wishlist Alert'),
        ('budget_tip','Budget Tip'),
        ('discovery','Discovery Suggestion'),
        ('seasonal_pick','Seasonal Pick'),
        ('trending','Trending Product'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='shopping_insights', verbose_name='Pengguna'
    )
    insight_type = models.CharField(max_length=30, choices=INSIGHT_TYPES, verbose_name='Tipe Insight')
    title = models.CharField(max_length=255, verbose_name='Judul')
    description = models.TextField(verbose_name='Deskripsi')
    action_text = models.CharField(max_length=100, blank=True, default='', verbose_name='Teks Aksi')
    action_url = models.CharField(max_length=500, blank=True, default='', verbose_name='URL Aksi')

    product = models.ForeignKey(
        'products.Product', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='shopping_insights', verbose_name='Produk'
    )
    store = models.ForeignKey(
        'stores.Store', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='shopping_insights', verbose_name='Toko'
    )

    supporting_data = models.JSONField(default=dict, blank=True)
    ai_generated = models.BooleanField(default=True)
    personalization_score = models.FloatField(default=0.0)

    is_read = models.BooleanField(default=False)
    is_dismissed = models.BooleanField(default=False)
    is_clicked = models.BooleanField(default=False)

    computed_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ai_shopping_insights'
        verbose_name = 'Personal Shopping Insight'
        verbose_name_plural = 'Personal Shopping Insights'
        indexes = [
            models.Index(fields=['user', 'insight_type']),
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['computed_at']),
        ]

    def __str__(self):
        return f'ShoppingInsight: {self.title} for {self.user.email}'


# ═══════════════════════════════════════════════════════════════
# 7. LEARNING ENGINE — AI Model Registry & Experiments
# ═══════════════════════════════════════════════════════════════

class AIModelRegistry(models.Model):
    """
    Registry of all AI models used across the platform.
    Tracks versions, performance, and accuracy over time.
    """
    MODEL_TYPES = [
        ('scoring','Scoring Engine'),
        ('prediction','Prediction Model'),
        ('segmentation','Segmentation Model'),
        ('recommendation','Recommendation Model'),
        ('nlp','NLP/Text Model'),
        ('vision','Vision Model'),
        ('fraud','Fraud Detection Model'),
        ('pricing','Pricing Model'),
        ('forecast','Forecasting Model'),
        ('churn','Churn Prediction Model'),
        ('clv','CLV Model'),
        ('sentiment','Sentiment Model'),
        ('gamification','Gamification Model'),
        ('orchestrator','AI Orchestrator'),
    ]

    name = models.CharField(max_length=100, verbose_name='Nama Model')
    model_type = models.CharField(max_length=30, choices=MODEL_TYPES, verbose_name='Tipe Model')
    version = models.CharField(max_length=50, verbose_name='Versi')
    description = models.TextField(blank=True, default='', verbose_name='Deskripsi')

    # Performance metrics
    accuracy = models.FloatField(default=0.0, verbose_name='Accuracy')
    precision = models.FloatField(default=0.0, verbose_name='Precision')
    recall = models.FloatField(default=0.0, verbose_name='Recall')
    f1_score = models.FloatField(default=0.0, verbose_name='F1 Score')
    mae = models.FloatField(null=True, blank=True, verbose_name='Mean Absolute Error')
    rmse = models.FloatField(null=True, blank=True, verbose_name='Root Mean Squared Error')

    # Training info
    training_data_size = models.IntegerField(default=0, verbose_name='Training Data Size')
    feature_count = models.IntegerField(default=0, verbose_name='Feature Count')
    training_duration_seconds = models.FloatField(default=0.0, verbose_name='Training Duration (s)')
    last_trained_at = models.DateTimeField(null=True, blank=True)

    # Deployment
    is_active = models.BooleanField(default=False, verbose_name='Active in Production')
    is_deprecated = models.BooleanField(default=False)
    deployed_at = models.DateTimeField(null=True, blank=True)
    deprecation_reason = models.TextField(blank=True, default='')

    # Gemini integration
    uses_gemini = models.BooleanField(default=False)
    gemini_model = models.CharField(max_length=100, blank=True, default='')
    prompt_template = models.TextField(blank=True, default='')

    # Source
    source_code_path = models.CharField(max_length=500, blank=True, default='')
    owner_team = models.CharField(max_length=100, blank=True, default='')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='Dibuat Oleh'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_model_registry'
        verbose_name = 'AI Model Registry'
        verbose_name_plural = 'AI Model Registry'
        indexes = [
            models.Index(fields=['model_type', 'is_active']),
            models.Index(fields=['model_type', 'version']),
        ]
        unique_together = [['name', 'version']]

    def __str__(self):
        return f'{self.name} v{self.version} ({self.get_model_type_display()})'


class ExperimentResult(models.Model):
    """
    Tracks A/B experiment and AI intervention results.
    Enables continuous learning and self-improvement.
    """
    STATUS_CHOICES = [
        ('running','Running'),('completed','Completed'),('cancelled','Cancelled'),
    ]

    name = models.CharField(max_length=200, verbose_name='Nama Experiment')
    description = models.TextField(blank=True, default='', verbose_name='Deskripsi')
    hypothesis = models.TextField(blank=True, default='', verbose_name='Hypothesis')

    # Experiment type
    experiment_type = models.CharField(max_length=50, verbose_name='Tipe Experiment',
        choices=[('notification','Notification'),('recommendation','Recommendation'),
                 ('pricing','Pricing'),('campaign','Campaign'),('ui','UI/UX'),
                 ('engagement','Engagement Strategy'),('gamification','Gamification'),
                 ('coach','Business Coach'),('algorithm','Algorithm Change')])

    # Variants
    control_name = models.CharField(max_length=100, blank=True, default='control', verbose_name='Control')
    variant_names = models.JSONField(default=list, blank=True, verbose_name='Variant Names')
    traffic_split = models.JSONField(default=dict, blank=True, verbose_name='Traffic Split %')

    # Results
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running')
    results = models.JSONField(default=dict, blank=True, verbose_name='Detailed Results')
    winner = models.CharField(max_length=100, blank=True, default='', verbose_name='Winner')
    significance_level = models.FloatField(default=0.0, verbose_name='Statistical Significance')
    effect_size = models.FloatField(default=0.0, verbose_name='Effect Size')

    # Sample
    sample_size = models.IntegerField(default=0, verbose_name='Total Sample Size')
    control_size = models.IntegerField(default=0)
    variant_sizes = models.JSONField(default=dict, blank=True)

    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_hours = models.IntegerField(default=72, verbose_name='Duration (hours)')

    # Learning
    key_learnings = models.TextField(blank=True, default='', verbose_name='Key Learnings')
    applied_to_production = models.BooleanField(default=False, verbose_name='Applied to Production?')
    applied_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='Dibuat Oleh'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_experiments'
        verbose_name = 'Experiment Result'
        verbose_name_plural = 'Experiment Results'
        indexes = [
            models.Index(fields=['experiment_type', 'status']),
            models.Index(fields=['status', 'started_at']),
        ]

    def __str__(self):
        return f'Experiment: {self.name} ({self.get_experiment_type_display()}, {self.status})'
