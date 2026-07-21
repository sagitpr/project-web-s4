"""
Admin configuration for SEO app.
Allows admins to manage per-page SEO metadata.
"""

from django.contrib import admin
from .models import SeoMetadata


@admin.register(SeoMetadata)
class SeoMetadataAdmin(admin.ModelAdmin):
    """
    Admin interface for managing per-page SEO metadata.
    """
    list_display = ['path', 'meta_title_preview', 'schema_type', 'noindex', 'is_active', 'updated_at']
    list_filter = ['schema_type', 'noindex', 'is_active', 'created_at']
    search_fields = ['path', 'meta_title', 'meta_description']
    ordering = ['path']
    
    fieldsets = [
        ('Page', {
            'fields': ['path', 'is_active'],
        }),
        ('Meta Tags', {
            'fields': ['meta_title', 'meta_description', 'meta_keywords'],
        }),
        ('Open Graph', {
            'fields': ['og_title', 'og_description', 'og_image'],
            'classes': ['collapse'],
        }),
        ('Indexing & Schema', {
            'fields': ['canonical_url', 'noindex', 'schema_type'],
        }),
        ('Advanced (JSON)', {
            'fields': ['breadcrumb_json', 'hreflang_json'],
            'classes': ['collapse'],
        }),
    ]
    
    def meta_title_preview(self, obj):
        if obj.meta_title:
            return obj.meta_title[:60] + ('...' if len(obj.meta_title) > 60 else '')
        return '(default)'
    meta_title_preview.short_description = 'Title'
    
    actions = ['mark_as_indexed', 'mark_as_noindex']
    
    def mark_as_indexed(self, request, queryset):
        queryset.update(noindex=False)
        self.message_user(request, f"{queryset.count()} page(s) marked as indexable.")
    mark_as_indexed.short_description = "Allow indexing (remove noindex)"
    
    def mark_as_noindex(self, request, queryset):
        queryset.update(noindex=True)
        self.message_user(request, f"{queryset.count()} page(s) marked as noindex.")
    mark_as_noindex.short_description = "Block indexing (add noindex)"
