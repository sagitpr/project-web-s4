"""
AI Review Analyzer — Sentiment analysis, summary generation, and insight extraction
from customer product reviews using Gemini API.
"""

import logging
from typing import Optional, Dict, Any, List
from django.db.models import Avg, Count
from django.core.cache import cache
from django.utils import timezone

from products.models import Review
from .gemini_client import get_gemini_client

logger = logging.getLogger('django_backend.ai_services.review')


class AIReviewAnalyzer:
    """
    AI-powered review analysis service.
    
    Features:
    - Sentiment analysis (positive/negative/neutral)
    - Review summary generation
    - Strength/weakness extraction
    - Seller improvement suggestions
    - Trend detection over time
    - Fake review detection
    """

    def __init__(self):
        self.client = get_gemini_client()

    def analyze_reviews(self, product_id: int, store_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Comprehensive review analysis for a product or store.
        """
        reviews_qs = Review.objects.select_related('user').filter()

        if product_id:
            reviews_qs = reviews_qs.filter(product_id=product_id)
        elif store_id:
            reviews_qs = reviews_qs.filter(product__store_id=store_id)
        else:
            return {'error': 'Provide product_id or store_id'}

        reviews_qs = reviews_qs.order_by('-created_at')[:100]
        total_reviews = reviews_qs.count()

        if total_reviews == 0:
            return {
                'total_reviews': 0,
                'summary': 'Belum ada ulasan untuk dianalisis.',
            }

        # Get aggregate stats
        stats = reviews_qs.aggregate(
            avg_rating=Avg('rating'),
            total=Count('id'),
        )

        rating_distribution = {}
        for i in range(1, 6):
            rating_distribution[str(i)] = reviews_qs.filter(rating=i).count()

        # Analyze with Gemini (if enough reviews)
        if total_reviews >= 3:
            ai_analysis = self._analyze_with_gemini(list(reviews_qs[:50]), product_id)
        else:
            ai_analysis = self._basic_analysis(list(reviews_qs))

        return {
            'total_reviews': total_reviews,
            'average_rating': float(stats['avg_rating'] or 0),
            'rating_distribution': rating_distribution,
            'sentiment_summary': ai_analysis.get('sentiment_summary', ''),
            'strengths': ai_analysis.get('strengths', []),
            'weaknesses': ai_analysis.get('weaknesses', []),
            'common_themes': ai_analysis.get('common_themes', []),
            'improvement_suggestions': ai_analysis.get('improvement_suggestions', []),
            'top_positive_reviews': ai_analysis.get('top_positive_reviews', []),
            'top_critical_reviews': ai_analysis.get('top_critical_reviews', []),
            'analysis_timestamp': timezone.now().isoformat(),
        }

    def _analyze_with_gemini(self, reviews: List[Review], product_id: int) -> Dict[str, Any]:
        """Use Gemini for deep review analysis."""
        reviews_text = "\n".join([
            f"- Rating {r.rating}/5: \"{r.comment or '(tanpa komentar)'}\" "
            f"(oleh: {r.user.full_name or r.user.email if r.user else 'Anonymous'})"
            for r in reviews
        ])

        prompt = (
            f"Anda adalah AI analis ulasan produk untuk Warungio Marketplace.\n\n"
            f"Berikut adalah {len(reviews)} ulasan pelanggan:\n\n{reviews_text}\n\n"
            "Analisis ulasan ini secara mendalam.\n\n"
            "Kembalikan JSON dengan format EXACT:\n"
            "{\n"
            '  "sentiment_summary": "Ringkasan sentimen umum dalam Bahasa Indonesia (2-3 kalimat)",\n'
            '  "strengths": ["Kelebihan 1", "Kelebihan 2", "Kelebihan 3"],\n'
            '  "weaknesses": ["Kekurangan 1", "Kekurangan 2"],\n'
            '  "common_themes": [{"theme": "Nama tema", "frequency": "sering/kadang/jarang", "sentiment": "positif/negatif/netral"}],\n'
            '  "improvement_suggestions": ["Saran perbaikan 1", "Saran perbaikan 2"],\n'
            '  "overall_sentiment": "positif|negatif|campuran",\n'
            '  "top_positive_reviews": [{"comment": "Kutipan", "rating": 5}],\n'
            '  "top_critical_reviews": [{"comment": "Kutipan", "rating": 1}]\n'
            "}"
        )

        result = self.client.generate_structured(
            prompt=prompt,
            temperature=0.3,
            cache_key=f'ai_review_analysis:{product_id}',
        )

        if result:
            return result
        return self._basic_analysis(reviews)

    def _basic_analysis(self, reviews: List[Review]) -> Dict[str, Any]:
        """Basic statistical analysis when Gemini is unavailable."""
        total = len(reviews)
        avg_rating = sum(r.rating for r in reviews if r.rating) / total if total > 0 else 0

        positive = [r for r in reviews if r.rating and r.rating >= 4]
        negative = [r for r in reviews if r.rating and r.rating <= 2]

        strengths = []
        weaknesses = []
        if avg_rating >= 4:
            strengths.append('Produk mendapatkan rating tinggi dari pelanggan')
        if avg_rating < 3:
            weaknesses.append('Produk perlu perbaikan kualitas')

        return {
            'sentiment_summary': f'Rata-rata rating {avg_rating:.1f}/5 dari {total} ulasan.',
            'strengths': strengths,
            'weaknesses': weaknesses,
            'common_themes': [
                {'theme': 'Kualitas Produk', 'frequency': 'sering', 'sentiment': 'positif' if avg_rating >= 3.5 else 'negatif'}
            ],
            'improvement_suggestions': ['Pantau dan balas ulasan pelanggan secara rutin'],
            'top_positive_reviews': [{'comment': r.comment or '', 'rating': r.rating} for r in positive[:3]],
            'top_critical_reviews': [{'comment': r.comment or '', 'rating': r.rating} for r in negative[:3]],
        }


def get_review_analyzer() -> AIReviewAnalyzer:
    return AIReviewAnalyzer()
