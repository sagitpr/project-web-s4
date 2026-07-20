"""
AI Product Recommendation Engine.
Analyzes user behavior, purchase history, wishlist, cart, and category preferences
to generate personalized product recommendations using Gemini API.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import timedelta
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.conf import settings

from accounts.models import User
from orders.models import Order, OrderItem, Cart
from products.models import Product, Favorite, RecentlyViewed
from stores.models import Store, StoreFollower
from .gemini_client import get_gemini_client

logger = logging.getLogger('django_backend.ai_services.recommendation')


class AIRecommendationEngine:
    """
    AI-powered product recommendation engine.
    
    Combines:
    - Collaborative filtering (what similar users bought)
    - Content-based filtering (user's purchase history, preferences)
    - Contextual recommendations (nearby stores, trending products)
    - Gemini AI for personalized explanations
    """

    def __init__(self, user: Optional[User] = None):
        self.user = user
        self.client = get_gemini_client()

    def get_personalized_recommendations(
        self,
        limit: int = 20,
        include_ai_explanation: bool = True,
    ) -> Dict[str, Any]:
        """
        Get personalized product recommendations for a user.
        
        Returns:
            Dict with categorized recommendations
        """
        if not self.user or not self.user.is_authenticated:
            return self._get_trending_recommendations(limit)

        today = timezone.now().date()
        month_ago = today - timedelta(days=30)

        # 1. Get user's purchase history categories
        purchased_categories = set()
        purchased_products = OrderItem.objects.filter(
            order__user=self.user,
            order__order_status__in=['paid', 'completed', 'shipped', 'processed'],
        ).values_list('product__category_id', flat=True).distinct()

        # 2. Get user's favorite categories
        favorite_categories = set()
        favorite_products = Favorite.objects.filter(
            user=self.user
        ).values_list('product__category_id', flat=True).distinct()
        favorite_categories.update(favorite_products)

        # 3. Get recently viewed categories
        viewed_categories = set()
        viewed_products = RecentlyViewed.objects.filter(
            user=self.user
        ).values_list('product__category_id', flat=True).distinct()[:20]
        viewed_categories.update(viewed_products)

        # 4. Get cart items
        cart = Cart.objects.filter(user=self.user).first()
        cart_product_ids = set()
        if cart:
            cart_product_ids = set(
                Cart.objects.filter(user=self.user)
                .values_list('product_id', flat=True)
            )

        # 5. Get user's followed stores
        followed_store_ids = set(
            StoreFollower.objects.filter(user=self.user)
            .values_list('store_id', flat=True)
        )

        # Merge all preference categories
        preference_categories = purchased_categories | favorite_categories | viewed_categories

        # Build recommendations from different sources
        recommendations = {
            'based_on_purchases': [],
            'based_on_favorites': [],
            'based_on_views': [],
            'from_followed_stores': [],
            'trending': [],
            'ai_personalized': [],
        }

        # Source 1: Products from purchased categories
        if purchased_categories:
            similar_products = Product.objects.filter(
                category_id__in=purchased_categories,
                is_active=True,
                stock__gt=0,
            ).exclude(
                Q(id__in=cart_product_ids)
            ).select_related('store', 'category').order_by('-sold_count', '-rating')[:8]
            
            recommendations['based_on_purchases'] = [
                self._product_to_dict(p) for p in similar_products
            ]

        # Source 2: Products from followed stores
        if followed_store_ids:
            store_products = Product.objects.filter(
                store_id__in=followed_store_ids,
                is_active=True,
                stock__gt=0,
            ).exclude(
                Q(id__in=cart_product_ids)
            ).select_related('store', 'category').order_by('-created_at')[:6]
            
            recommendations['from_followed_stores'] = [
                self._product_to_dict(p) for p in store_products
            ]

        # Source 3: Trending products
        trending = Product.objects.filter(
            is_active=True,
            stock__gt=0,
        ).select_related('store', 'category').order_by('-sold_count', '-rating')[:10]

        recommendations['trending'] = [
            self._product_to_dict(p) for p in trending
        ]

        # Source 4: AI-powered personalized recommendations
        if include_ai_explanation and preference_categories:
            ai_recs = self._get_ai_recommendations(
                list(preference_categories)[:5],
                followed_store_ids,
                limit=6,
            )
            if ai_recs:
                recommendations['ai_personalized'] = ai_recs

        return recommendations

    def _get_ai_recommendations(
        self,
        category_ids: List[int],
        store_ids: set,
        limit: int = 6,
    ) -> List[Dict]:
        """Use Gemini AI to generate personalized recommendations with explanations."""
        from products.models import Category
        
        categories = Category.objects.filter(id__in=category_ids)
        category_names = [c.category_name for c in categories if c]

        # Get candidate products
        candidates = Product.objects.filter(
            category_id__in=category_ids,
            is_active=True,
            stock__gt=0,
        ).select_related('store', 'category').order_by('-rating', '-sold_count')[:20]

        if not candidates:
            return []

        product_list = "\n".join([
            f"- {p.product_name} (ID: {p.id}, Kategori: {p.category.category_name if p.category else 'N/A'}, "
            f"Harga: Rp {p.price:,.0f}, Rating: {p.rating or 0}, Terjual: {p.sold_count})"
            for p in candidates
        ])

        prompt = (
            f"Anda adalah AI rekomendasi produk untuk Warungio Marketplace.\n\n"
            f"Pengguna memiliki preferensi di kategori: {', '.join(category_names)}\n\n"
            f"Berikut adalah produk yang tersedia:\n{product_list}\n\n"
            f"Pilih {min(limit, len(candidates))} produk terbaik untuk direkomendasikan kepada pengguna ini.\n"
            f"Pertimbangkan: rating tinggi, banyak terjual, harga kompetitif.\n\n"
            f"Kembalikan JSON array dengan format:\n"
            f"[{{\"product_id\": int, \"reason\": \"Alasan rekomendasi dalam Bahasa Indonesia (1 kalimat)\"}}]"
        )

        result = self.client.generate_structured(
            prompt=prompt,
            temperature=0.3,
        )

        if not result or not isinstance(result, list):
            return []

        product_map = {p.id: p for p in candidates}
        recommendations = []
        for rec in result:
            pid = rec.get('product_id')
            if pid in product_map:
                p = product_map[pid]
                recommendations.append({
                    **self._product_to_dict(p),
                    'ai_reason': rec.get('reason', 'Direkomendasikan untuk Anda'),
                })

        return recommendations

    def _get_trending_recommendations(self, limit: int = 20) -> Dict[str, Any]:
        """Get trending products for unauthenticated users."""
        trending = Product.objects.filter(
            is_active=True,
            stock__gt=0,
        ).select_related('store', 'category').order_by('-sold_count', '-rating')[:limit]

        return {
            'trending': [self._product_to_dict(p) for p in trending],
            'ai_personalized': [],
        }

    def get_similar_products(
        self,
        product_id: int,
        limit: int = 8,
        use_ai: bool = True,
    ) -> List[Dict]:
        """
        Get similar products based on category and features.
        Uses Gemini AI for intelligent similarity analysis when use_ai=True.
        """
        try:
            product = Product.objects.select_related('category', 'store').get(id=product_id)
        except Product.DoesNotExist:
            return []

        # Base: products in same category
        same_category = Product.objects.filter(
            category=product.category,
            is_active=True,
            stock__gt=0,
        ).exclude(id=product_id).select_related('store').order_by('-rating')[:limit]

        if not same_category:
            return []

        if use_ai:
            return self._get_ai_similar_products(product, list(same_category), limit)

        return [self._product_to_dict(p) for p in same_category]

    def _get_ai_similar_products(
        self,
        product: Product,
        candidates: List[Product],
        limit: int,
    ) -> List[Dict]:
        """Use Gemini to rank similar products intelligently."""
        product_info = (
            f"Produk: {product.product_name}\n"
            f"Kategori: {product.category.category_name if product.category else 'N/A'}\n"
            f"Harga: Rp {product.price:,.0f}\n"
            f"Deskripsi: {product.description or 'Tidak ada deskripsi'}"
        )

        candidates_info = "\n".join([
            f"- {p.product_name} (ID: {p.id}, Harga: Rp {p.price:,.0f}, Rating: {p.rating or 0})"
            for p in candidates
        ])

        prompt = (
            f"Anda adalah AI rekomendasi produk.\n\n"
            f"Produk Referensi:\n{product_info}\n\n"
            f"Produk Kandidat:\n{candidates_info}\n\n"
            f"Pilih {min(limit, len(candidates))} produk yang PALING MIRIP dengan produk referensi.\n"
            f"Pertimbangkan: kategori, harga, dan kesesuaian penggunaan.\n\n"
            f"Kembalikan JSON array:\n"
            f"[{{\"product_id\": int, \"relevance_score\": float 0-1, \"reason\": \"Alasan dalam Bahasa Indonesia\"}}]"
        )

        result = self.client.generate_structured(
            prompt=prompt,
            temperature=0.2,
        )

        if not result or not isinstance(result, list):
            return [self._product_to_dict(p) for p in candidates[:limit]]

        candidate_map = {p.id: p for p in candidates}
        ranked = []
        for rec in sorted(result, key=lambda x: x.get('relevance_score', 0), reverse=True):
            pid = rec.get('product_id')
            if pid in candidate_map:
                p = candidate_map[pid]
                ranked.append({
                    **self._product_to_dict(p),
                    'relevance_score': rec.get('relevance_score', 0.5),
                    'ai_reason': rec.get('reason', ''),
                })

        return ranked[:limit]

    def _product_to_dict(self, product) -> Dict:
        """Convert product model to recommendation-ready dict."""
        return {
            'id': product.id,
            'product_name': product.product_name,
            'price': float(product.price),
            'price_formatted': f"Rp {product.price:,.0f}",
            'image_url': product.image_url or '',
            'rating': float(product.rating or 0),
            'sold_count': product.sold_count or 0,
            'stock': product.stock or 0,
            'unit': product.unit or 'pcs',
            'store_name': product.store.store_name if product.store else '',
            'store_id': product.store.id if product.store else None,
            'category_name': product.category.category_name if product.category else '',
            'category_id': product.category.id if product.category else None,
            'is_available': product.stock > 0 if product.stock else False,
        }


def get_recommendation_engine(user=None) -> AIRecommendationEngine:
    """Get recommendation engine instance."""
    return AIRecommendationEngine(user)
