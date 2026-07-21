"""
SEO Metadata model for Warungio Marketplace.
Allows admins to edit per-page SEO metadata via Django admin.
"""

from django.db import models
from django.utils.text import slugify


class SeoMetadata(models.Model):
    """
    Per-page SEO metadata that can be edited via Django admin.
    
    When a SeoMetadata record exists for a given path, the context
    processor will use it instead of the hardcoded _PAGE_SEO dict.
    """
    # The URL path this SEO data applies to (e.g., "/", "/info/tentang-kami/")
    path = models.CharField(
        max_length=500,
        unique=True,
        help_text="URL path, e.g. '/info/tentang-kami/' or '/' for root",
        db_index=True,
    )
    
    # Meta tags
    meta_title = models.CharField(
        max_length=120,
        blank=True,
        help_text="HTML <title> tag (max 120 chars for SEO)"
    )
    meta_description = models.TextField(
        max_length=320,
        blank=True,
        help_text="Meta description (aim for 155-160 chars, max 320)"
    )
    meta_keywords = models.CharField(
        max_length=500,
        blank=True,
        help_text="Comma-separated keywords"
    )
    
    # Open Graph
    og_title = models.CharField(
        max_length=120,
        blank=True,
        help_text="Open Graph title (defaults to meta_title if empty)"
    )
    og_description = models.TextField(
        max_length=320,
        blank=True,
        help_text="Open Graph description (defaults to meta_description if empty)"
    )
    og_image = models.URLField(
        max_length=500,
        blank=True,
        help_text="Open Graph image URL (e.g., /static/images/og-default.png)"
    )
    
    # Canonical & indexing
    canonical_url = models.CharField(
        max_length=500,
        blank=True,
        help_text="Custom canonical URL (leave empty to auto-generate from path)"
    )
    noindex = models.BooleanField(
        default=False,
        help_text="Check to add noindex, nofollow to this page"
    )
    
    # Schema.org type
    SCHEMA_CHOICES = [
        ('WebPage', 'WebPage'),
        ('AboutPage', 'AboutPage'),
        ('ContactPage', 'ContactPage'),
        ('FAQPage', 'FAQPage'),
        ('Blog', 'Blog'),
        ('Article', 'Article'),
        ('Product', 'Product'),
        ('CollectionPage', 'CollectionPage'),
        ('SearchResultsPage', 'SearchResultsPage'),
        ('ItemPage', 'ItemPage'),
        ('ProfilePage', 'ProfilePage'),
    ]
    schema_type = models.CharField(
        max_length=50,
        choices=SCHEMA_CHOICES,
        default='WebPage',
        help_text="Schema.org @type for this page"
    )
    
    # Breadcrumb (JSON)
    breadcrumb_json = models.TextField(
        blank=True,
        help_text='JSON array of breadcrumb items, e.g. [{"label":"Home","url":"/"}]'
    )
    
    # Hreflang
    hreflang_json = models.TextField(
        blank=True,
        help_text='JSON object of hreflang alternates, e.g. {"en":"/en/about/"}'
    )
    
    # Status & timestamps
    is_active = models.BooleanField(default=True, help_text="Uncheck to use hardcoded defaults")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "SEO Metadata"
        verbose_name_plural = "SEO Metadata"
        ordering = ['path']
    
    def __str__(self):
        return f"SEO: {self.path} → {self.meta_title or '(default)'}"
    
    def clean(self):
        """Normalize path: ensure trailing slash (except root)."""
        if self.path and self.path != '/':
            self.path = self.path.rstrip('/') + '/'
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    @classmethod
    def get_for_path(cls, path):
        """Get SeoMetadata for a path, or None."""
        if path != '/':
            path = path.rstrip('/') + '/'
        try:
            return cls.objects.get(path=path, is_active=True)
        except cls.DoesNotExist:
            return None
