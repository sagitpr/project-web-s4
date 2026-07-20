"""
Engagement & Retention Engine Models for Warungio Marketplace.

Core Models:
- UserBehaviorProfile: Holistic behavioral profile per user
- EngagementProfile: Real-time engagement metrics and scoring
- RetentionProfile: Retention tracking and analysis
- ChurnPrediction: ML-based churn prediction results
- BehaviorEvent: Typed user action events
- ActivityLog: Time-series activity data
- DeviceToken: FCM/Web Push device registration
- NotificationTemplate: AI-generated message templates
- NotificationCampaign: Campaign management
- NotificationQueue: Queued notifications for delivery
- NotificationAnalytics: Delivery and engagement analytics
- NotificationABTest: A/B testing for notification variants
- NotificationDeliveryLog: Individual delivery tracking
- QuietHoursConfig: Per-user quiet hours
- EngagementSignal: Configuration for event triggers
- NotificationCooldown: Cooldown tracking per type per user
"""

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal


# ═══════════════════════════════════════════════════════════════
# USER BEHAVIOR & PROFILING
# ═══════════════════════════════════════════════════════════════

class UserBehaviorProfile(models.Model):
    """
    Holistic behavioral profile for each user.
    Continuously computed from all user interactions.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='behavior_profile', verbose_name='Pengguna'
    )

    # ── Login & Session Patterns ──
    last_login_at = models.DateTimeField(null=True, blank=True)
    last_logout_at = models.DateTimeField(null=True, blank=True)
    total_logins = models.IntegerField(default=0)
    total_sessions = models.IntegerField(default=0)
    avg_session_duration_minutes = models.FloatField(default=0.0)
    login_streak_days = models.IntegerField(default=0)
    longest_streak_days = models.IntegerField(default=0)
    last_streak_broken_at = models.DateTimeField(null=True, blank=True)

    # ── Active Hours ──
    preferred_hour_start = models.IntegerField(default=8, validators=[MinValueValidator(0), MaxValueValidator(23)])
    preferred_hour_end = models.IntegerField(default=22, validators=[MinValueValidator(0), MaxValueValidator(23)])
    peak_activity_hour = models.IntegerField(default=10, validators=[MinValueValidator(0), MaxValueValidator(23)])
    weekend_active = models.BooleanField(default=True)
    night_owl = models.BooleanField(default=False)

    # ── Browsing & Purchase ──
    total_products_viewed = models.IntegerField(default=0)
    total_searches = models.IntegerField(default=0)
    avg_search_to_purchase_minutes = models.FloatField(default=0.0)
    total_cart_adds = models.IntegerField(default=0)
    total_cart_abandons = models.IntegerField(default=0)
    cart_abandon_rate = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    total_orders = models.IntegerField(default=0)
    total_spent = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    avg_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_wishlist_adds = models.IntegerField(default=0)
    total_wishlist_removes = models.IntegerField(default=0)
    favorite_categories = models.JSONField(default=list, blank=True)
    top_bought_products = models.JSONField(default=list, blank=True)
    top_bought_stores = models.JSONField(default=list, blank=True)

    # ── AI Smart Scan Usage ──
    total_ai_scans = models.IntegerField(default=0)
    total_ai_freshness_checks = models.IntegerField(default=0)
    total_ai_search_queries = models.IntegerField(default=0)
    total_recommendation_clicks = models.IntegerField(default=0)

    # ── Reviews & Social ──
    total_reviews = models.IntegerField(default=0)
    avg_rating_given = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(5.0)])
    total_stores_followed = models.IntegerField(default=0)
    total_referrals = models.IntegerField(default=0)
    total_chat_messages = models.IntegerField(default=0)

    # ── Payment & Delivery ──
    preferred_payment_method = models.CharField(max_length=50, blank=True, default='')
    total_payment_failures = models.IntegerField(default=0)
    total_deliveries = models.IntegerField(default=0)
    delivery_satisfaction_score = models.FloatField(default=0.0)

    # ── Loyalty & Rewards ──
    total_loyalty_points = models.IntegerField(default=0)
    loyalty_tier = models.CharField(max_length=50, blank=True, default='bronze')
    reward_progress_pct = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(100.0)])
    rewards_redeemed = models.IntegerField(default=0)

    # ── Engagement Quality ──
    engagement_score = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(100.0)])
    activity_score = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(100.0)])
    retention_score = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(100.0)])
    loyalty_score = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(100.0)])
    churn_risk_score = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(100.0)])
    notification_fatigue_score = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(100.0)])

    # ── Notification Effectiveness ──
    total_notifications_sent = models.IntegerField(default=0)
    total_notifications_opened = models.IntegerField(default=0)
    total_notification_clicks = models.IntegerField(default=0)
    notification_open_rate = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    notification_ctr = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    last_notification_interaction_at = models.DateTimeField(null=True, blank=True)
    optimal_notification_hour = models.IntegerField(default=10)

    # ── Timezone & Location ──
    timezone = models.CharField(max_length=50, default='Asia/Jakarta')
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    city = models.CharField(max_length=100, blank=True, default='')
    province = models.CharField(max_length=100, blank=True, default='')

    # ── Inactivity Tracking ──
    inactivity_days = models.IntegerField(default=0)
    last_active_at = models.DateTimeField(null=True, blank=True)
    is_at_risk = models.BooleanField(default=False)
    risk_level = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('at_risk', 'At Risk'),
            ('dormant', 'Dormant'),
            ('churned', 'Churned'),
            ('reactivated', 'Reactivated'),
        ],
        default='active'
    )
    risk_level_changed_at = models.DateTimeField(null=True, blank=True)

    # ── Metadata ──
    profile_version = models.IntegerField(default=1)
    computed_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'engagement_user_profiles'
        verbose_name = 'Profil Perilaku Pengguna'
        verbose_name_plural = 'Profil Perilaku Pengguna'
        indexes = [
            models.Index(fields=['user', 'computed_at']),
            models.Index(fields=['churn_risk_score']),
            models.Index(fields=['engagement_score']),
            models.Index(fields=['risk_level']),
            models.Index(fields=['notification_open_rate']),
            models.Index(fields=['inactivity_days']),
        ]

    def __str__(self):
        return f'BehaviorProfile: {self.user.email} (risk={self.risk_level}, engagement={self.engagement_score:.1f})'


class BehaviorEvent(models.Model):
    """
    Typed user action events for behavioral analysis.
    Every meaningful user action creates an event record.
    """
    EVENT_TYPES = [
        # Auth & Session
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('registration', 'Registration'),
        ('otp_verified', 'OTP Verified'),
        ('password_reset', 'Password Reset'),

        # Browsing
        ('page_view', 'Page View'),
        ('product_view', 'Product View'),
        ('category_view', 'Category View'),
        ('search_query', 'Search Query'),
        ('ai_search', 'AI Search'),

        # Cart
        ('cart_add', 'Cart Add'),
        ('cart_remove', 'Cart Remove'),
        ('cart_update', 'Cart Update'),
        ('cart_abandon', 'Cart Abandon'),

        # Favorites/Wishlist
        ('wishlist_add', 'Wishlist Add'),
        ('wishlist_remove', 'Wishlist Remove'),

        # Orders
        ('order_created', 'Order Created'),
        ('order_paid', 'Order Paid'),
        ('order_cancelled', 'Order Cancelled'),
        ('order_completed', 'Order Completed'),
        ('order_refunded', 'Order Refunded'),

        # Payment
        ('payment_started', 'Payment Started'),
        ('payment_success', 'Payment Success'),
        ('payment_failed', 'Payment Failed'),

        # Delivery
        ('delivery_update', 'Delivery Update'),
        ('delivery_completed', 'Delivery Completed'),

        # AI Services
        ('ai_scan', 'AI Smart Scan'),
        ('ai_freshness_check', 'AI Freshness Check'),
        ('ai_recommendation_click', 'AI Recommendation Click'),
        ('ai_chat', 'AI Chat'),

        # Social
        ('review_written', 'Review Written'),
        ('store_follow', 'Store Follow'),
        ('store_unfollow', 'Store Unfollow'),
        ('referral_made', 'Referral Made'),
        ('chat_message', 'Chat Message'),

        # Loyalty
        ('points_earned', 'Points Earned'),
        ('points_redeemed', 'Points Redeemed'),
        ('tier_upgrade', 'Tier Upgrade'),
        ('reward_claimed', 'Reward Claimed'),

        # Notifications
        ('notification_received', 'Notification Received'),
        ('notification_opened', 'Notification Opened'),
        ('notification_clicked', 'Notification Clicked'),
        ('notification_dismissed', 'Notification Dismissed'),

        # Custom Events
        ('custom_event', 'Custom Event'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='behavior_events', verbose_name='Pengguna'
    )
    event_type = models.CharField(
        max_length=50, choices=EVENT_TYPES, db_index=True,
        verbose_name='Tipe Event'
    )
    event_category = models.CharField(
        max_length=50, blank=True, default='',
        help_text='Grouping category for the event (e.g., "auth", "browsing", "cart")'
    )

    # Context
    source = models.CharField(
        max_length=50, blank=True, default='',
        help_text='Source of the event (web, mobile, api, system)'
    )
    url = models.CharField(max_length=500, blank=True, default='')
    referrer = models.CharField(max_length=500, blank=True, default='')

    # Data payload
    data = models.JSONField(default=dict, blank=True, verbose_name='Data Event')
    value = models.FloatField(null=True, blank=True, help_text='Numeric value associated with event')

    # Device & Location
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')
    device_type = models.CharField(
        max_length=20, blank=True, default='',
        choices=[('mobile', 'Mobile'), ('tablet', 'Tablet'), ('desktop', 'Desktop')]
    )
    session_id = models.CharField(max_length=100, blank=True, default='')

    # Timestamps
    event_time = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'engagement_behavior_events'
        verbose_name = 'Event Perilaku'
        verbose_name_plural = 'Event Perilaku'
        indexes = [
            models.Index(fields=['user', 'event_type']),
            models.Index(fields=['user', 'event_time']),
            models.Index(fields=['event_type', 'event_time']),
            models.Index(fields=['event_category', 'event_time']),
        ]

    def __str__(self):
        return f'{self.event_type} by {self.user.email} at {self.event_time}'


class ActivityLog(models.Model):
    """
    Time-series aggregated activity data.
    Stores daily/weekly/monthly activity summaries per user.
    """
    ACTIVITY_TYPE_CHOICES = [
        ('login', 'Login'),
        ('purchase', 'Purchase'),
        ('browse', 'Browse'),
        ('search', 'Search'),
        ('cart', 'Cart Activity'),
        ('wishlist', 'Wishlist'),
        ('review', 'Review'),
        ('ai_scan', 'AI Scan'),
        ('chat', 'Chat'),
        ('referral', 'Referral'),
        ('notification_interaction', 'Notification Interaction'),
    ]

    PERIOD_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='activity_logs', verbose_name='Pengguna'
    )
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_TYPE_CHOICES, verbose_name='Tipe Aktivitas')
    period = models.CharField(max_length=20, choices=PERIOD_CHOICES, verbose_name='Periode')
    period_start = models.DateTimeField(verbose_name='Awal Periode')
    period_end = models.DateTimeField(verbose_name='Akhir Periode')
    count = models.IntegerField(default=0, verbose_name='Jumlah')
    duration_minutes = models.FloatField(default=0.0, verbose_name='Durasi (menit)')
    value = models.FloatField(null=True, blank=True, verbose_name='Nilai')
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'engagement_activity_logs'
        verbose_name = 'Log Aktivitas'
        verbose_name_plural = 'Log Aktivitas'
        indexes = [
            models.Index(fields=['user', 'activity_type', 'period']),
            models.Index(fields=['user', 'period_start']),
            models.Index(fields=['activity_type', 'period_start']),
        ]
        unique_together = [['user', 'activity_type', 'period', 'period_start']]

    def __str__(self):
        return f'{self.activity_type} ({self.period}): {self.count} for {self.user.email}'


# ═══════════════════════════════════════════════════════════════
# CHURN PREDICTION
# ═══════════════════════════════════════════════════════════════

class ChurnPrediction(models.Model):
    """
    ML-based churn prediction results for each user.
    Stores probability scores and contributing factors.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='churn_prediction', verbose_name='Pengguna'
    )
    churn_probability = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        verbose_name='Probabilitas Churn'
    )
    churn_risk_category = models.CharField(
        max_length=20,
        choices=[
            ('very_low', 'Very Low (<10%)'),
            ('low', 'Low (10-25%)'),
            ('moderate', 'Moderate (25-50%)'),
            ('high', 'High (50-75%)'),
            ('very_high', 'Very High (>75%)'),
        ],
        verbose_name='Kategori Risiko'
    )
    predicted_churn_date = models.DateField(null=True, blank=True, verbose_name='Prediksi Tanggal Churn')

    # Contributing factors (JSON with factor names and weights)
    top_factors = models.JSONField(default=list, blank=True, verbose_name='Faktor Utama')

    # Model metadata
    model_version = models.CharField(max_length=50, blank=True, default='', verbose_name='Versi Model')
    confidence_score = models.FloatField(default=0.0, verbose_name='Skor Keyakinan')
    features_used = models.IntegerField(default=0, verbose_name='Fitur Digunakan')

    # Recommendation
    intervention_suggestion = models.TextField(blank=True, default='', verbose_name='Saran Intervensi')
    recommended_action = models.CharField(
        max_length=50, blank=True, default='',
        choices=[
            ('re_engagement_push', 'Push Re-engagement'),
            ('discount_offer', 'Discount Offer'),
            ('personalized_recommendation', 'Personalized Recommendation'),
            ('loyalty_boost', 'Loyalty Boost'),
            ('feedback_request', 'Feedback Request'),
            ('no_action', 'No Action Needed'),
        ],
        verbose_name='Aksi yang Direkomendasikan'
    )

    computed_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'engagement_churn_predictions'
        verbose_name = 'Prediksi Churn'
        verbose_name_plural = 'Prediksi Churn'
        indexes = [
            models.Index(fields=['churn_probability']),
            models.Index(fields=['churn_risk_category']),
            models.Index(fields=['computed_at']),
        ]

    def __str__(self):
        return f'ChurnPrediction: {self.user.email} ({self.churn_risk_category}, {self.churn_probability:.1%})'


# ═══════════════════════════════════════════════════════════════
# DEVICE TOKENS (FCM / Web Push)
# ═══════════════════════════════════════════════════════════════

class DeviceToken(models.Model):
    """
    Device tokens for push notification delivery.
    Supports FCM (Android), Web Push (PWA/Browser), and future APNs (iOS).
    """
    PLATFORM_CHOICES = [
        ('fcm_android', 'FCM Android'),
        ('fcm_ios', 'FCM iOS (via APNs)'),
        ('web_push', 'Web Push (PWA)'),
        ('apns', 'Apple APNs'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='device_tokens', verbose_name='Pengguna'
    )
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, verbose_name='Platform')
    token = models.TextField(verbose_name='Token')
    device_name = models.CharField(max_length=255, blank=True, default='', verbose_name='Nama Perangkat')
    device_id = models.CharField(max_length=255, blank=True, default='', verbose_name='ID Perangkat')
    app_version = models.CharField(max_length=20, blank=True, default='', verbose_name='Versi Aplikasi')
    is_active = models.BooleanField(default=True, verbose_name='Aktif')
    last_used_at = models.DateTimeField(null=True, blank=True, verbose_name='Terakhir Digunakan')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'engagement_device_tokens'
        verbose_name = 'Token Perangkat'
        verbose_name_plural = 'Token Perangkat'
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['platform', 'is_active']),
            models.Index(fields=['token']),
        ]
        unique_together = [['token', 'platform']]

    def __str__(self):
        return f'{self.platform} token for {self.user.email}'


# ═══════════════════════════════════════════════════════════════
# NOTIFICATION TEMPLATES & GENERATION
# ═══════════════════════════════════════════════════════════════

class NotificationTemplate(models.Model):
    """
    Templates for AI-generated notification messages.
    Uses psychological triggers to maximize engagement.
    """
    TRIGGER_CHOICES = [
        # Psychological Triggers
        ('curiosity_gap', 'Curiosity Gap'),
        ('loss_aversion', 'Loss Aversion'),
        ('fomo', 'FOMO (Fear of Missing Out)'),
        ('social_proof', 'Social Proof'),
        ('goal_gradient', 'Goal Gradient Effect'),
        ('habit_loop', 'Habit Loop'),
        ('variable_reward', 'Variable Reward'),
        ('positive_reinforcement', 'Positive Reinforcement'),
        ('personalization', 'Personalization'),
        ('scarcity', 'Scarcity'),
        ('reciprocity', 'Reciprocity'),
        ('progress_motivation', 'Progress Motivation'),

        # Event Triggers
        ('registration', 'Registration Complete'),
        ('otp_verified', 'OTP Verified'),
        ('login', 'User Login'),
        ('logout', 'User Logout'),
        ('inactivity', 'Inactivity Detected'),
        ('abandoned_cart', 'Abandoned Cart'),
        ('wishlist_update', 'Wishlist Update'),
        ('new_product', 'New Product Available'),
        ('low_stock', 'Low Stock Alert'),
        ('stock_refill', 'Stock Refill'),
        ('flash_sale', 'Flash Sale'),
        ('order_update', 'Order Update'),
        ('payment_event', 'Payment Event'),
        ('delivery_tracking', 'Delivery Tracking'),
        ('ai_recommendation', 'AI Recommendation'),
        ('loyalty_reward', 'Loyalty Reward'),
        ('seller_performance', 'Seller Performance'),
        ('new_review', 'New Review'),
        ('referral', 'Referral Program'),
        ('birthday', 'Birthday'),
        ('holiday', 'Holiday Greeting'),
        ('weather_change', 'Weather Change'),
        ('regional_event', 'Regional Event'),
        ('security_alert', 'Security Alert'),
        ('fraud_detection', 'Fraud Detection'),
        ('maintenance', 'Maintenance Notice'),
        ('custom_event', 'Custom Event'),
    ]

    NOTIFICATION_CHANNEL_CHOICES = [
        ('push', 'Push Notification'),
        ('email', 'Email'),
        ('in_app', 'In-App Notification'),
        ('whatsapp', 'WhatsApp'),
        ('sms', 'SMS'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    name = models.CharField(max_length=100, verbose_name='Nama Template')
    trigger_type = models.CharField(
        max_length=50, choices=TRIGGER_CHOICES,
        verbose_name='Tipe Trigger Psikologis'
    )
    channel = models.CharField(
        max_length=20, choices=NOTIFICATION_CHANNEL_CHOICES, default='push',
        verbose_name='Channel Notifikasi'
    )

    # Template content with placeholders
    title_template = models.CharField(max_length=255, verbose_name='Template Judul')
    body_template = models.TextField(verbose_name='Template Isi')
    action_text_template = models.CharField(max_length=100, blank=True, default='', verbose_name='Template Teks Aksi')
    action_url_template = models.CharField(max_length=500, blank=True, default='', verbose_name='Template URL Aksi')

    # Configuration
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    icon = models.CharField(max_length=100, blank=True, default='')
    image_url = models.CharField(max_length=500, blank=True, default='')
    ttl_seconds = models.IntegerField(default=86400, help_text='Time-to-live in seconds (default: 24h)')

    # AI Generation config
    use_ai_generation = models.BooleanField(default=True, verbose_name='Gunakan AI Generation')
    ai_temperature = models.FloatField(default=0.7, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    ai_system_prompt = models.TextField(blank=True, default='', verbose_name='System Prompt untuk AI')

    # A/B Testing config
    ab_test_enabled = models.BooleanField(default=False)
    ab_test_variants = models.JSONField(default=list, blank=True)

    # Cooldown config
    cooldown_hours = models.IntegerField(default=24, help_text='Cooldown between same trigger type')
    max_per_day = models.IntegerField(default=3, help_text='Max notifications per day for this type')

    # Status
    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField(default=False, help_text='System templates cannot be deleted')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'engagement_notification_templates'
        verbose_name = 'Template Notifikasi AI'
        verbose_name_plural = 'Template Notifikasi AI'
        indexes = [
            models.Index(fields=['trigger_type', 'is_active']),
            models.Index(fields=['channel', 'is_active']),
        ]

    def __str__(self):
        return f'{self.name} ({self.get_trigger_type_display()})'


# ═══════════════════════════════════════════════════════════════
# NOTIFICATION CAMPAIGNS
# ═══════════════════════════════════════════════════════════════

class NotificationCampaign(models.Model):
    """
    Campaign management for scheduled notification blasts.
    Supports targeted campaigns to user segments.
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('running', 'Running'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    TARGET_TYPE_CHOICES = [
        ('all_users', 'All Users'),
        ('buyers', 'All Buyers'),
        ('sellers', 'All Sellers'),
        ('risk_segment', 'Risk Segment'),
        ('tier_segment', 'Loyalty Tier Segment'),
        ('inactive_users', 'Inactive Users'),
        ('custom_segment', 'Custom Segment'),
        ('ab_test', 'A/B Test'),
    ]

    name = models.CharField(max_length=200, verbose_name='Nama Kampanye')
    description = models.TextField(blank=True, default='', verbose_name='Deskripsi')

    template = models.ForeignKey(
        NotificationTemplate, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='campaigns',
        verbose_name='Template'
    )

    # Targeting
    target_type = models.CharField(
        max_length=30, choices=TARGET_TYPE_CHOICES,
        default='buyers', verbose_name='Tipe Target'
    )
    target_filter = models.JSONField(
        default=dict, blank=True,
        verbose_name='Filter Target (JSON query)'
    )
    target_count = models.IntegerField(default=0, verbose_name='Jumlah Target')

    # Scheduling
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    scheduled_at = models.DateTimeField(null=True, blank=True, verbose_name='Dijadwalkan Pada')
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Delivery config
    channel = models.CharField(
        max_length=20, choices=NotificationTemplate.NOTIFICATION_CHANNEL_CHOICES,
        default='push', verbose_name='Channel'
    )
    use_ai_personalization = models.BooleanField(default=True, verbose_name='Gunakan AI Personalisasi')
    max_notifications_per_user = models.IntegerField(default=1, verbose_name='Maks Notifikasi per User')

    # Results
    total_sent = models.IntegerField(default=0)
    total_delivered = models.IntegerField(default=0)
    total_opened = models.IntegerField(default=0)
    total_clicked = models.IntegerField(default=0)
    total_converted = models.IntegerField(default=0)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_campaigns',
        verbose_name='Dibuat Oleh'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'engagement_campaigns'
        verbose_name = 'Kampanye Notifikasi'
        verbose_name_plural = 'Kampanye Notifikasi'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['scheduled_at']),
            models.Index(fields=['target_type']),
        ]

    def __str__(self):
        return self.name


# ═══════════════════════════════════════════════════════════════
# NOTIFICATION QUEUE
# ═══════════════════════════════════════════════════════════════

class NotificationQueue(models.Model):
    """
    Queued notifications awaiting intelligent delivery.
    The AI Timing Engine picks items from this queue.
    """
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('scheduled', 'Scheduled for Delivery'),
        ('delivering', 'Delivering'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
        ('rate_limited', 'Rate Limited'),
        ('cooldown', 'In Cooldown'),
        ('duplicate', 'Duplicate (Skipped)'),
        ('quiet_hours', 'Held for Quiet Hours'),
    ]

    PRIORITY_CHOICES = [
        (0, 'Low'),
        (1, 'Normal'),
        (2, 'High'),
        (3, 'Urgent'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='notification_queue', verbose_name='Pengguna'
    )
    campaign = models.ForeignKey(
        NotificationCampaign, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='queue_items',
        verbose_name='Kampanye'
    )

    # Notification content (pre-rendered)
    title = models.CharField(max_length=255, verbose_name='Judul')
    body = models.TextField(verbose_name='Isi')
    action_url = models.CharField(max_length=500, blank=True, default='')
    action_text = models.CharField(max_length=100, blank=True, default='')
    icon = models.CharField(max_length=100, blank=True, default='')
    image_url = models.CharField(max_length=500, blank=True, default='')
    data = models.JSONField(default=dict, blank=True, verbose_name='Data Payload')

    # Trigger info
    trigger_type = models.CharField(
        max_length=50, blank=True, default='',
        verbose_name='Tipe Trigger'
    )
    trigger_ref_id = models.CharField(
        max_length=100, blank=True, default='',
        verbose_name='Referensi Trigger (order_id, product_id, etc.)'
    )

    # Delivery config
    channel = models.CharField(
        max_length=20, choices=DeviceToken.PLATFORM_CHOICES + [('in_app', 'In-App')],
        default='fcm_android', verbose_name='Channel Pengiriman'
    )
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=1, verbose_name='Prioritas')

    # AI-generated metadata
    psychological_trigger = models.CharField(
        max_length=50, blank=True, default='',
        verbose_name='Trigger Psikologis yang Digunakan'
    )
    ai_generated = models.BooleanField(default=False, verbose_name='Dihasilkan AI')
    ai_model_version = models.CharField(max_length=50, blank=True, default='', verbose_name='Versi Model AI')
    personalization_score = models.FloatField(default=0.0, verbose_name='Skor Personalisasi')

    # Timing
    scheduled_for = models.DateTimeField(null=True, blank=True, verbose_name='Dijadwalkan Pada')
    delivered_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    converted_at = models.DateTimeField(null=True, blank=True)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    status_message = models.CharField(max_length=255, blank=True, default='')
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)

    # A/B Test tracking
    ab_test_group = models.CharField(max_length=20, blank=True, default='', verbose_name='Grup A/B Test')
    ab_test_variant = models.CharField(max_length=50, blank=True, default='')

    # Feeedback
    feedback_score = models.IntegerField(null=True, blank=True, verbose_name='Skor Feedback (1-5)')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'engagement_notification_queue'
        verbose_name = 'Antrian Notifikasi AI'
        verbose_name_plural = 'Antrian Notifikasi AI'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'scheduled_for']),
            models.Index(fields=['priority', 'status']),
            models.Index(fields=['trigger_type', 'status']),
            models.Index(fields=['scheduled_for']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f'Queue[{self.id}] {self.title} → {self.user.email} ({self.get_status_display()})'


# ═══════════════════════════════════════════════════════════════
# NOTIFICATION ANALYTICS
# ═══════════════════════════════════════════════════════════════

class NotificationDeliveryLog(models.Model):
    """
    Individual delivery record for detailed analytics.
    Tracks every send attempt, delivery confirmation, and user interaction.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent to Provider'),
        ('delivered', 'Delivered to Device'),
        ('opened', 'Opened by User'),
        ('clicked', 'Clicked by User'),
        ('converted', 'Converted (purchase/action)'),
        ('failed', 'Delivery Failed'),
        ('expired', 'Expired Before Delivery'),
        ('dismissed', 'Dismissed by User'),
    ]

    queue_item = models.ForeignKey(
        NotificationQueue, on_delete=models.CASCADE,
        related_name='delivery_logs', verbose_name='Item Antrian'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='notification_logs', verbose_name='Pengguna'
    )

    # Device info
    device_token = models.ForeignKey(
        DeviceToken, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='delivery_logs',
        verbose_name='Token Perangkat'
    )
    platform = models.CharField(max_length=20, blank=True, default='', verbose_name='Platform')

    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    status_message = models.CharField(max_length=255, blank=True, default='')
    provider_response = models.TextField(blank=True, default='', verbose_name='Response Provider')

    # Timing
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    converted_at = models.DateTimeField(null=True, blank=True)
    # Latency tracking
    send_latency_ms = models.IntegerField(null=True, blank=True, help_text='Time from queue to provider')
    delivery_latency_ms = models.IntegerField(null=True, blank=True, help_text='Time from provider to device')

    # Retry info
    attempt_number = models.IntegerField(default=1)
    is_retry = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'engagement_delivery_logs'
        verbose_name = 'Log Pengiriman Notifikasi'
        verbose_name_plural = 'Log Pengiriman Notifikasi'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['queue_item', 'status']),
            models.Index(fields=['sent_at']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f'DeliveryLog[{self.id}] {self.status} for {self.user.email}'


class NotificationAnalytics(models.Model):
    """
    Aggregated notification analytics per user per period.
    Used for dashboard and adaptive frequency control.
    """
    PERIOD_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='notification_analytics', verbose_name='Pengguna'
    )
    period = models.CharField(max_length=20, choices=PERIOD_CHOICES, verbose_name='Periode')
    period_start = models.DateTimeField(verbose_name='Awal Periode')
    period_end = models.DateTimeField(verbose_name='Akhir Periode')

    # Volume
    total_queued = models.IntegerField(default=0)
    total_sent = models.IntegerField(default=0)
    total_delivered = models.IntegerField(default=0)
    total_failed = models.IntegerField(default=0)

    # Engagement
    total_opened = models.IntegerField(default=0)
    total_clicked = models.IntegerField(default=0)
    total_converted = models.IntegerField(default=0)
    total_dismissed = models.IntegerField(default=0)

    # Derived rates
    delivery_rate = models.FloatField(default=0.0)
    open_rate = models.FloatField(default=0.0)
    click_through_rate = models.FloatField(default=0.0)
    conversion_rate = models.FloatField(default=0.0)

    # By trigger type
    by_trigger = models.JSONField(default=dict, blank=True, verbose_name='Per Trigger Type')

    # By psychological trigger
    by_psychological_trigger = models.JSONField(default=dict, blank=True, verbose_name='Per Psikologis Trigger')

    # By hour (24-element array)
    by_hour = models.JSONField(default=list, blank=True, verbose_name='Per Jam')

    # Fatigue score
    fatigue_score = models.FloatField(default=0.0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'engagement_notification_analytics'
        verbose_name = 'Analitik Notifikasi'
        verbose_name_plural = 'Analitik Notifikasi'
        indexes = [
            models.Index(fields=['user', 'period', 'period_start']),
            models.Index(fields=['period', 'period_start']),
        ]
        unique_together = [['user', 'period', 'period_start']]

    def __str__(self):
        return f'Analytics: {self.user.email} ({self.period}) — sent:{self.total_sent} open:{self.open_rate:.1%}'


# ═══════════════════════════════════════════════════════════════
# A/B TESTING
# ═══════════════════════════════════════════════════════════════

class NotificationABTest(models.Model):
    """
    A/B testing framework for notification variants.
    Tests different titles, bodies, triggers, timing, and channels.
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    name = models.CharField(max_length=200, verbose_name='Nama A/B Test')
    description = models.TextField(blank=True, default='', verbose_name='Deskripsi')

    # Test variants (JSON array of variant objects)
    variants = models.JSONField(default=list, blank=True, verbose_name='Varian')

    # Targeting
    test_size = models.IntegerField(default=1000, verbose_name='Ukuran Sampel')
    control_percentage = models.FloatField(
        default=50.0, validators=[MinValueValidator(1.0), MaxValueValidator(99.0)],
        verbose_name='Persentase Kontrol'
    )

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Test parameters
    test_duration_hours = models.IntegerField(default=72, verbose_name='Durasi Test (jam)')
    min_sample_per_variant = models.IntegerField(default=100, verbose_name='Min Sample per Varian')
    confidence_threshold = models.FloatField(
        default=0.95, verbose_name='Threshold Keyakinan',
        help_text='Statistical significance threshold (default: 0.95)'
    )

    # Results
    results = models.JSONField(default=dict, blank=True, verbose_name='Hasil')
    winning_variant = models.CharField(max_length=50, blank=True, default='')
    significance_level = models.FloatField(default=0.0, verbose_name='Tingkat Signifikansi')

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='Dibuat Oleh'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'engagement_ab_tests'
        verbose_name = 'A/B Test Notifikasi'
        verbose_name_plural = 'A/B Test Notifikasi'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f'ABTest: {self.name} ({self.get_status_display()})'


# ═══════════════════════════════════════════════════════════════
# QUIET HOURS & COOLDOWN
# ═══════════════════════════════════════════════════════════════

class QuietHoursConfig(models.Model):
    """
    Per-user quiet hours configuration.
    Extends the existing NotificationPreference with AI-optimized settings.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='quiet_hours_config', verbose_name='Pengguna'
    )

    # Manual quiet hours
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)

    # AI-recommended quiet hours (learned from user behavior)
    ai_quiet_hours_start = models.TimeField(null=True, blank=True)
    ai_quiet_hours_end = models.TimeField(null=True, blank=True)

    # Cooldown settings
    global_cooldown_minutes = models.IntegerField(default=30, verbose_name='Cooldown Global (menit)')
    cooldown_per_type = models.JSONField(
        default=dict, blank=True,
        verbose_name='Cooldown per Tipe (menit)'
    )

    # Frequency caps
    max_push_per_hour = models.IntegerField(default=3, verbose_name='Max Push per Jam')
    max_push_per_day = models.IntegerField(default=15, verbose_name='Max Push per Hari')
    max_email_per_day = models.IntegerField(default=3, verbose_name='Max Email per Hari')

    # Weekend/off-hours optimization
    weekend_quiet_mode = models.BooleanField(default=True)
    reduce_at_night = models.BooleanField(default=True)
    night_hour_start = models.IntegerField(default=21, verbose_name='Jam Malam Mulai')
    night_hour_end = models.IntegerField(default=8, verbose_name='Jam Malam Selesai')

    # Adaptive frequency control
    adaptive_frequency_enabled = models.BooleanField(default=True)
    adaptive_base_frequency = models.IntegerField(
        default=3, verbose_name='Frekuensi Dasar per Hari',
        help_text='Base notifications per day'
    )
    adaptive_max_frequency = models.IntegerField(
        default=10, verbose_name='Frekuensi Maksimum per Hari',
        help_text='Maximum notifications per day when engagement is high'
    )

    use_ai_optimization = models.BooleanField(default=True, verbose_name='Gunakan Optimasi AI')

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'engagement_quiet_hours'
        verbose_name = 'Konfigurasi Quiet Hours'
        verbose_name_plural = 'Konfigurasi Quiet Hours'

    def __str__(self):
        return f'QuietHours: {self.user.email}'


class NotificationCooldown(models.Model):
    """
    Tracks cooldown status per notification type per user.
    Prevents notification spam by enforcing time-based cooldowns.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='notification_cooldowns', verbose_name='Pengguna'
    )
    trigger_type = models.CharField(
        max_length=50, choices=NotificationTemplate.TRIGGER_CHOICES,
        verbose_name='Tipe Trigger'
    )
    last_sent_at = models.DateTimeField(verbose_name='Terakhir Dikirim')
    cooldown_until = models.DateTimeField(verbose_name='Cooldown Hingga')
    sent_count_today = models.IntegerField(default=0, verbose_name='Dikirim Hari Ini')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'engagement_notification_cooldowns'
        verbose_name = 'Cooldown Notifikasi'
        verbose_name_plural = 'Cooldown Notifikasi'
        unique_together = [['user', 'trigger_type']]
        indexes = [
            models.Index(fields=['user', 'cooldown_until']),
            models.Index(fields=['cooldown_until']),
        ]

    def __str__(self):
        return f'Cooldown[{self.trigger_type}] for {self.user.email} until {self.cooldown_until}'


# ═══════════════════════════════════════════════════════════════
# ENGAGEMENT SIGNALS (Event Triggers)
# ═══════════════════════════════════════════════════════════════

class EngagementSignal(models.Model):
    """
    Configuration for event triggers that automatically create
    engagement notifications. Each signal maps a behavior event
    to a notification template with conditions.
    """
    SIGNAL_TYPE_CHOICES = [
        ('event_based', 'Event-Based'),
        ('time_based', 'Time-Based'),
        ('threshold_based', 'Threshold-Based'),
        ('behavioral', 'Behavioral'),
        ('external', 'External API'),
    ]

    name = models.CharField(max_length=100, verbose_name='Nama Signal')
    description = models.TextField(blank=True, default='', verbose_name='Deskripsi')

    signal_type = models.CharField(
        max_length=30, choices=SIGNAL_TYPE_CHOICES,
        verbose_name='Tipe Signal'
    )

    # Event mapping
    event_type = models.CharField(
        max_length=50, choices=BehaviorEvent.EVENT_TYPES,
        blank=True, default='',
        verbose_name='Tipe Event'
    )

    # Template
    template = models.ForeignKey(
        NotificationTemplate, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='signals',
        verbose_name='Template Notifikasi'
    )

    # Conditions (JSON query for filtering)
    conditions = models.JSONField(
        default=dict, blank=True,
        verbose_name='Kondisi (JSON)'
    )

    # Priority
    priority = models.IntegerField(
        choices=[(0, 'Low'), (1, 'Normal'), (2, 'High'), (3, 'Urgent')],
        default=1, verbose_name='Prioritas'
    )

    # Cooldown
    cooldown_minutes = models.IntegerField(default=1440, verbose_name='Cooldown (menit)')

    # Enable AI generation for this signal
    use_ai_generation = models.BooleanField(default=True)
    use_ai_timing = models.BooleanField(default=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'engagement_signals'
        verbose_name = 'Signal Engagement'
        verbose_name_plural = 'Signal Engagement'
        indexes = [
            models.Index(fields=['event_type', 'is_active']),
            models.Index(fields=['signal_type', 'is_active']),
        ]

    def __str__(self):
        return f'{self.name} ({self.get_signal_type_display()})'


# ═══════════════════════════════════════════════════════════════
# NOTIFICATION PREFERENCE EXTENSION
# ═══════════════════════════════════════════════════════════════

class NotificationPreferenceExtension(models.Model):
    """
    Extends the base NotificationPreference model with
    engagement-specific preferences and AI-optimized settings.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='engagement_prefs', verbose_name='Pengguna'
    )

    # AI optimization opt-in
    ai_optimization_enabled = models.BooleanField(
        default=True, verbose_name='Optimasi AI Aktif',
        help_text='Allow AI to optimize notification timing and content'
    )
    ai_learning_enabled = models.BooleanField(
        default=True, verbose_name='AI Learning Aktif',
        help_text='Allow AI to learn from user behavior patterns'
    )

    # Channel preferences (fine-grained)
    push_engagement = models.BooleanField(default=True, verbose_name='Push Engagement')
    push_recommendations = models.BooleanField(default=True, verbose_name='Push Rekomendasi')
    push_reminders = models.BooleanField(default=True, verbose_name='Push Pengingat')
    email_engagement = models.BooleanField(default=False, verbose_name='Email Engagement')
    email_digest_frequency = models.CharField(
        max_length=20, blank=True, default='weekly',
        choices=[('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly'), ('never', 'Never')],
        verbose_name='Frekuensi Email Digest'
    )

    # Psychological trigger preferences
    allowed_psychological_triggers = models.JSONField(
        default=list, blank=True,
        verbose_name='Trigger Psikologis yang Diizinkan',
        help_text='Empty list means all triggers allowed'
    )

    # Notification categories opt-in
    engagement_categories = models.JSONField(
        default=dict, blank=True,
        verbose_name='Kategori Engagement',
        help_text='{"category_name": true/false}'
    )

    # Personalization level
    personalization_level = models.CharField(
        max_length=20, default='full',
        choices=[
            ('full', 'Full Personalization'),
            ('moderate', 'Moderate Personalization'),
            ('minimal', 'Minimal Personalization'),
            ('none', 'No Personalization'),
        ],
        verbose_name='Tingkat Personalisasi'
    )

    # Do not disturb mode
    do_not_disturb = models.BooleanField(default=False, verbose_name='Jangan Ganggu')
    dnd_until = models.DateTimeField(null=True, blank=True, verbose_name='DND Hingga')

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'engagement_preference_extensions'
        verbose_name = 'Ekstensi Preferensi Notifikasi'
        verbose_name_plural = 'Ekstensi Preferensi Notifikasi'

    def __str__(self):
        return f'EngagementPrefs: {self.user.email}'
