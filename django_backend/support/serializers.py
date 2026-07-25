"""
Support / Help Center serializers for Warungio Marketplace API.
"""

from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.openapi import OpenApiTypes
from .models import (
    HelpCategory, HelpArticle, FAQ, BannerPromo,
    ContactInfo, SupportInfo, ChatQuickReply, SupportTicket,
    Complaint, ReportProduct, ReportSeller, ReportBuyer,
    Dispute, InternalNote,
)


class HelpCategorySerializer(serializers.ModelSerializer):
    article_count = serializers.SerializerMethodField()

    class Meta:
        model = HelpCategory
        fields = ('id', 'name', 'slug', 'icon', 'description', 'sort_order', 'article_count')

    @extend_schema_field(OpenApiTypes.STR)


    def get_article_count(self, obj):
        return obj.articles.filter(is_published=True).count()


class HelpArticleListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.SlugField(source='category.slug', read_only=True)

    class Meta:
        model = HelpArticle
        fields = ('id', 'title', 'slug', 'excerpt', 'category', 'category_name',
                  'category_slug', 'views_count', 'is_featured', 'published_at')
        read_only_fields = ('views_count',)


class HelpArticleDetailSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = HelpArticle
        fields = ('id', 'title', 'slug', 'content', 'excerpt', 'category', 'category_name',
                  'featured_image', 'views_count', 'helpful_count', 'not_helpful_count',
                  'is_featured', 'tags', 'published_at', 'created_at', 'updated_at')
        read_only_fields = ('views_count', 'helpful_count', 'not_helpful_count')


class FAQSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = FAQ
        fields = ('id', 'question', 'answer', 'category', 'category_name', 'sort_order')


class BannerPromoSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = BannerPromo
        fields = ('id', 'title', 'subtitle', 'image_url', 'link_url', 'link_text',
                  'position', 'sort_order')

    @extend_schema_field(OpenApiTypes.STR)


    def get_image_url(self, obj):
        if obj.image:
            return obj.image.url
        return None


class ContactInfoSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_contact_type_display', read_only=True)

    class Meta:
        model = ContactInfo
        fields = ('id', 'contact_type', 'type_display', 'label', 'value', 'icon',
                  'operating_hours', 'sort_order')


class SupportInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportInfo
        fields = ('id', 'key', 'title', 'description', 'icon', 'sort_order')


class SupportTicketSerializer(serializers.ModelSerializer):
    """Support ticket serializer."""
    user_name = serializers.CharField(source='user.full_name', read_only=True, allow_null=True)
    user_email = serializers.EmailField(source='user.email', read_only=True, allow_null=True)

    class Meta:
        model = SupportTicket
        fields = ('id', 'user', 'user_name', 'user_email', 'subject', 'message',
                  'support_status', 'priority', 'created_at', 'updated_at')
        read_only_fields = ('user', 'created_at', 'updated_at')


class ChatQuickReplySerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = ChatQuickReply
        fields = ('id', 'category', 'category_display', 'label', 'message_template', 'sort_order')


# =============================================================================
# CUSTOMER SUPPORT CENTER SERIALIZERS
# =============================================================================


class SupportTicketDetailSerializer(serializers.ModelSerializer):
    """Enhanced support ticket serializer with assignment and SLA details."""
    user_name = serializers.CharField(source='user.full_name', read_only=True, allow_null=True)
    user_email = serializers.EmailField(source='user.email', read_only=True, allow_null=True)
    assigned_to_name = serializers.CharField(source='assigned_to.full_name', read_only=True, allow_null=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    status_display = serializers.CharField(source='get_support_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)

    class Meta:
        model = SupportTicket
        fields = '__all__'
        read_only_fields = ('user', 'created_at', 'updated_at', 'first_response_at', 'resolved_at', 'sla_met')


class TicketAssignSerializer(serializers.Serializer):
    """Serializer for assigning a ticket to an admin."""
    assigned_to_id = serializers.IntegerField(required=True)
    note = serializers.CharField(required=False, allow_blank=True)


class ComplaintSerializer(serializers.ModelSerializer):
    """Complaint serializer."""
    user_name = serializers.CharField(source='user.full_name', read_only=True, allow_null=True)
    complaint_type_display = serializers.CharField(source='get_complaint_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Complaint
        fields = '__all__'
        read_only_fields = ('user', 'assigned_to', 'status', 'resolved_at', 'created_at', 'updated_at')


class ReportProductSerializer(serializers.ModelSerializer):
    """Product report serializer."""
    reporter_name = serializers.CharField(source='reporter.full_name', read_only=True, allow_null=True)
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True, allow_null=True)

    class Meta:
        model = ReportProduct
        fields = '__all__'
        read_only_fields = ('reporter', 'status', 'moderated_by', 'created_at', 'updated_at')


class ReportSellerSerializer(serializers.ModelSerializer):
    """Seller report serializer."""
    reporter_name = serializers.CharField(source='reporter.full_name', read_only=True, allow_null=True)
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ReportSeller
        fields = '__all__'
        read_only_fields = ('reporter', 'status', 'moderated_by', 'created_at', 'updated_at')


class ReportBuyerSerializer(serializers.ModelSerializer):
    """Buyer report serializer."""
    reporter_name = serializers.CharField(source='reporter.full_name', read_only=True, allow_null=True)
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ReportBuyer
        fields = '__all__'
        read_only_fields = ('reporter', 'status', 'moderated_by', 'created_at', 'updated_at')


class DisputeSerializer(serializers.ModelSerializer):
    """Dispute resolution serializer."""
    opened_by_name = serializers.CharField(source='opened_by.full_name', read_only=True, allow_null=True)
    against_name = serializers.CharField(source='against_user.full_name', read_only=True, allow_null=True)
    dispute_type_display = serializers.CharField(source='get_dispute_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    resolution_display = serializers.CharField(source='get_resolution_display', read_only=True, allow_null=True)

    class Meta:
        model = Dispute
        fields = '__all__'
        read_only_fields = ('mediator', 'resolution', 'resolved_at', 'created_at', 'updated_at')


class InternalNoteSerializer(serializers.ModelSerializer):
    """Internal note serializer."""
    author_name = serializers.CharField(source='author.full_name', read_only=True, allow_null=True)

    class Meta:
        model = InternalNote
        fields = '__all__'
        read_only_fields = ('author', 'created_at', 'updated_at')


class SupportDashboardSerializer(serializers.Serializer):
    """Support center dashboard stats."""
    total_tickets = serializers.IntegerField()
    open_tickets = serializers.IntegerField()
    pending_tickets = serializers.IntegerField()
    solved_tickets = serializers.IntegerField()
    urgent_tickets = serializers.IntegerField()
    unassigned_tickets = serializers.IntegerField()
    avg_response_time_hours = serializers.FloatField()
    sla_breach_count = serializers.IntegerField()
    total_complaints = serializers.IntegerField()
    pending_complaints = serializers.IntegerField()
    total_reports = serializers.IntegerField()
    pending_reports = serializers.IntegerField()
