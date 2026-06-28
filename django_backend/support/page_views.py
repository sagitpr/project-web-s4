"""
HTML page views for Bantuan & Chat Customer Service pages.
"""

from django.shortcuts import render, get_object_or_404
from django.core import serializers
from django.utils import timezone
from .models import (
    HelpCategory, HelpArticle, FAQ, BannerPromo,
    ContactInfo, SupportInfo, ChatQuickReply
)


def bantuan_page(request):
    """Render the Bantuan & Chat Customer Service page."""
    categories = HelpCategory.objects.filter(is_active=True)
    articles = HelpArticle.objects.filter(is_published=True).order_by('-is_featured', '-published_at')[:8]
    featured_articles = HelpArticle.objects.filter(is_published=True, is_featured=True)[:3]
    faqs = FAQ.objects.filter(is_published=True)[:6]
    banners = BannerPromo.objects.filter(
        is_active=True,
        position__in=['help_hero', 'help_bottom']
    )
    contacts = ContactInfo.objects.filter(is_active=True)
    support_infos = SupportInfo.objects.filter(is_active=True)
    quick_replies = ChatQuickReply.objects.filter(is_active=True)

    # Serialize articles as JSON for frontend search
    articles_data = []
    for art in articles:
        articles_data.append({
            'id': art.id,
            'title': art.title,
            'slug': art.slug,
            'excerpt': art.excerpt or '',
        })
    import json

    context = {
        'categories': categories,
        'articles': articles,
        'featured_articles': featured_articles,
        'faqs': faqs,
        'banners': banners,
        'contacts': contacts,
        'support_infos': support_infos,
        'quick_replies': quick_replies,
        'page_title': 'Bantuan',
        'articles_json': json.dumps(articles_data),
        'now': timezone.now(),
    }
    return render(request, 'helpcenter/bantuan.html', context)


def bantuan_article(request, slug):
    """Render a single help article page."""
    article = get_object_or_404(HelpArticle, slug=slug, is_published=True)
    article.increment_views()
    related_articles = HelpArticle.objects.filter(
        category=article.category, is_published=True
    ).exclude(id=article.id)[:4]

    context = {
        'article': article,
        'related_articles': related_articles,
        'page_title': article.title,
    }
    return render(request, 'helpcenter/article.html', context)
