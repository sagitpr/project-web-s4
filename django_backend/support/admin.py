"""
Support / Help Center admin configuration for Warungio Marketplace.
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    HelpCategory, HelpArticle, FAQ, BannerPromo,
    ContactInfo, SupportInfo, ChatQuickReply,
    SupportTicket, SupportConversation, SupportMessage,
    Complaint, ReportProduct, ReportSeller, ReportBuyer,
    Dispute, InternalNote,
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


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'subject', 'user', 'category', 'support_status', 'priority', 'assigned_to', 'created_at')
    list_filter = ('support_status', 'priority', 'category')
    search_fields = ('subject', 'message', 'user__email')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(SupportConversation)
class SupportConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'subject', 'user', 'is_active', 'is_resolved', 'created_at')
    list_filter = ('is_active', 'is_resolved')


@admin.register(SupportMessage)
class SupportMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'sender', 'is_from_user', 'is_read', 'created_at')
    list_filter = ('is_read', 'is_from_user')


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'complaint_type', 'status', 'assigned_to', 'order', 'created_at')
    list_filter = ('status', 'complaint_type')
    search_fields = ('description', 'user__email')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ReportProduct)
class ReportProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'reporter', 'reason', 'status', 'risk_score', 'created_at')
    list_filter = ('status', 'reason', 'is_auto_flagged')
    search_fields = ('description', 'product__name', 'reporter__email')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ReportSeller)
class ReportSellerAdmin(admin.ModelAdmin):
    list_display = ('id', 'seller', 'store', 'reporter', 'reason', 'status', 'created_at')
    list_filter = ('status', 'reason')
    search_fields = ('description', 'seller__email')


@admin.register(ReportBuyer)
class ReportBuyerAdmin(admin.ModelAdmin):
    list_display = ('id', 'buyer', 'reporter', 'reason', 'status', 'created_at')
    list_filter = ('status', 'reason')
    search_fields = ('description', 'buyer__email')


@admin.register(Dispute)
class DisputeAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'dispute_type', 'status', 'opened_by', 'mediator', 'created_at')
    list_filter = ('status', 'dispute_type')
    search_fields = ('description',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(InternalNote)
class InternalNoteAdmin(admin.ModelAdmin):
    list_display = ('id', 'note_type', 'reference_id', 'author', 'created_at')
    list_filter = ('note_type',)
    search_fields = ('content',)
