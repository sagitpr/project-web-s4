"""
Support / Help Center admin configuration for Warungio Marketplace.
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    HelpCategory, HelpArticle, FAQ, BannerPromo,
    ContactInfo, SupportInfo, ChatQuickReply
)


@admin.register(HelpCategory)
class HelpCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'sort_order', 'is_active', 'article_count')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('sort_order', 'is_active')

    def article_count(self, obj):
        return obj.articles.count()
    article_count.short_description = 'Jumlah Artikel'


@admin.register(HelpArticle)
class HelpArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'is_published', 'is_featured', 'views_count', 'helpful_count', 'published_at')
    list_filter = ('is_published', 'is_featured', 'category')
    search_fields = ('title', 'content', 'tags')
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ('is_published', 'is_featured')
    readonly_fields = ('views_count', 'helpful_count', 'not_helpful_count')
    fieldsets = (
        ('Informasi Artikel', {
            'fields': ('category', 'title', 'slug', 'content', 'excerpt', 'tags')
        }),
        ('Media', {
            'fields': ('featured_image', 'attachment'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_published', 'is_featured', 'sort_order', 'published_at')
        }),
        ('Statistik', {
            'fields': ('views_count', 'helpful_count', 'not_helpful_count'),
            'classes': ('collapse',)
        }),
    )


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'category', 'sort_order', 'is_published')
    list_filter = ('is_published', 'category')
    search_fields = ('question', 'answer')
    list_editable = ('sort_order', 'is_published')


@admin.register(BannerPromo)
class BannerPromoAdmin(admin.ModelAdmin):
    list_display = ('title', 'position', 'is_active', 'sort_order', 'banner_preview')
    list_filter = ('position', 'is_active')
    search_fields = ('title', 'subtitle')
    list_editable = ('is_active', 'sort_order')

    def banner_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height:50px" />', obj.image.url)
        return '-'
    banner_preview.short_description = 'Preview'


@admin.register(ContactInfo)
class ContactInfoAdmin(admin.ModelAdmin):
    list_display = ('contact_type', 'label', 'value', 'is_active', 'operating_hours')
    list_filter = ('contact_type', 'is_active')
    search_fields = ('label', 'value')
    list_editable = ('is_active',)


@admin.register(SupportInfo)
class SupportInfoAdmin(admin.ModelAdmin):
    list_display = ('key', 'title', 'is_active', 'sort_order')
    list_filter = ('is_active',)
    search_fields = ('title', 'description')
    list_editable = ('is_active', 'sort_order')


@admin.register(ChatQuickReply)
class ChatQuickReplyAdmin(admin.ModelAdmin):
    list_display = ('label', 'category', 'sort_order', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('label', 'message_template')
    list_editable = ('sort_order', 'is_active')
