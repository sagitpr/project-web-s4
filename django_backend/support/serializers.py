"""
Support / Help Center serializers for Warungio Marketplace API.
"""

from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.openapi import OpenApiTypes
from .models import (
    HelpCategory, HelpArticle, FAQ, BannerPromo,
    ContactInfo, SupportInfo, ChatQuickReply, SupportTicket
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
