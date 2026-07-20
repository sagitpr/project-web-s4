"""
AI Seller Assistant — Business intelligence for sellers.
Generates pricing suggestions, stock recommendations, sales analysis,
customer trends, and promotion recommendations using Gemini API.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import timedelta
from django.db.models import Sum, Avg, Count, Q, F
from django.utils import timezone
from django.core.cache import cache

from orders.models import Order, OrderItem
from products.models import Product, Review, Category
from stores.models import Store, StoreFollower
from .gemini_client import get_gemini_client

logger = logging.getLogger('django_backend.ai_services.seller')


class AISellerAssistant:
    """
    AI-powered seller assistant.
    
    Features:
    - Pricing suggestions based on market analysis
    - Stock recommendations
    - Sales performance analysis
    - Customer behavior trends
    - Promotion recommendations
    - Inventory optimization
    """

    def __init__(self, store):
        self.store = store
        self.client = get_gemini_client()

    def get_comprehensive_analysis(self, days: int = 30) -> Dict[str, Any]:
        """Full business analysis with AI insights."""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        prev_start = start_date - timedelta(days=days)

        # Gather data
        products = Product.objects.filter(store=self.store, is_active=True)
        
        # Sales data
        current_orders = Order.objects.filter(
            store=self.store,
            created_at__date__gte=start_date,
        )
        prev_orders = Order.objects.filter(
            store=self.store,
            created_at__date__gte=prev_start,
            created_at__date__lt=start_date,
        )

        current_revenue = current_orders.aggregate(t=Sum('total_price'))['t'] or 0
        prev_revenue = prev_orders.aggregate(t=Sum('total_price'))['t'] or 0
        current_count = current_orders.count()
        prev_count = prev_orders.count()
        
        revenue_growth = ((current_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0
        order_growth = ((current_count - prev_count) / prev_count * 100) if prev_count > 0 else 0

        # Product performance
        top_products = OrderItem.objects.filter(
            order__store=self.store,
            order__created_at__date__gte=start_date,
        ).values('product_id').annotate(
            total=Sum('qty'),
            revenue=Sum('subtotal')
        ).order_by('-total')[:5]

        # Low performing products
        all_product_ids = set(products.values_list('id', flat=True))
        selling_ids = set(OrderItem.objects.filter(
            order__store=self.store,
            order__created_at__date__gte=start_date,
        ).values_list('product_id', flat=True))
        unsold_ids = all_product_ids - selling_ids
        unsold_count = len(unsold_ids)

        # Followers
        follower_count = StoreFollower.objects.filter(store=self.store).count()

        # Reviews
        review_stats = Review.objects.filter(
            product__store=self.store
        ).aggregate(
            avg=Avg('rating'),
            count=Count('id')
        )

        # Pricing analysis
        pricing_analysis = self._analyze_pricing(products, days)

        # AI-generated insights
        ai_insights = self._generate_ai_insights(
            store_name=self.store.store_name,
            days=days,
            current_revenue=current_revenue,
            prev_revenue=prev_revenue,
            revenue_growth=revenue_growth,
            current_orders=current_count,
            order_growth=order_growth,
            total_products=products.count(),
            unsold_products=unsold_count,
            top_products=list(top_products),
            avg_rating=review_stats.get('avg') or 0,
            total_reviews=review_stats.get('count') or 0,
            follower_count=follower_count,
        )

        return {
            'store_name': self.store.store_name,
            'period_days': days,
            'sales_summary': {
                'current_revenue': float(current_revenue),
                'prev_revenue': float(prev_revenue),
                'revenue_growth_percent': round(revenue_growth, 1),
                'current_orders': current_count,
                'order_growth_percent': round(order_growth, 1),
                'avg_order_value': float(current_revenue / current_count) if current_count > 0 else 0,
            },
            'products_summary': {
                'total_active': products.count(),
                'out_of_stock': products.filter(Q(stock=0) | Q(stock__isnull=True)).count(),
                'low_stock': products.filter(stock__gt=0, stock__lte=5).count(),
                'unsold_products': unsold_count,
                'stock_value': sum(float(p.price or 0) * (p.stock or 0) for p in products),
            },
            'customer_summary': {
                'total_followers': follower_count,
                'average_rating': round(float(review_stats.get('avg') or 0), 1),
                'total_reviews': review_stats.get('count') or 0,
            },
            'pricing_insights': pricing_analysis,
            'ai_insights': ai_insights,
            'generated_at': timezone.now().isoformat(),
        }

    def _analyze_pricing(self, products, days: int) -> Dict[str, Any]:
        """Analyze pricing against market and suggest optimizations."""
        store_products = list(products.select_related('category').filter(
            category__isnull=False
        )[:20])

        if not store_products:
            return {'suggestions': [], 'market_position': 'unknown'}

        # Compare with similar products (same categories)
        categories = [p.category_id for p in store_products if p.category]
        similar_products = Product.objects.filter(
            category_id__in=categories,
            is_active=True,
        ).exclude(store=self.store)

        pricing_suggestions = []
        for p in store_products:
            similar = similar_products.filter(category=p.category)
            avg_price = similar.aggregate(avg=Avg('price'))['avg']
            
            if avg_price and p.price:
                price_ratio = float(p.price) / float(avg_price)
                if price_ratio > 1.2:
                    pricing_suggestions.append({
                        'product_id': p.id,
                        'product_name': p.product_name,
                        'current_price': float(p.price),
                        'market_avg': float(avg_price),
                        'suggestion': 'Pertimbangkan turunkan harga',
                        'ratio': round(price_ratio, 2),
                    })
                elif price_ratio < 0.8:
                    pricing_suggestions.append({
                        'product_id': p.id,
                        'product_name': p.product_name,
                        'current_price': float(p.price),
                        'market_avg': float(avg_price),
                        'suggestion': 'Harga kompetitif, bisa naikkan',
                        'ratio': round(price_ratio, 2),
                    })

        return {
            'suggestions': pricing_suggestions[:10],
            'total_analyzed': len(store_products),
            'market_position': 'premium' if len(pricing_suggestions) > 0 else 'competitive',
        }

    def _generate_ai_insights(self, **data) -> Dict[str, Any]:
        """Use Gemini AI to generate actionable business insights."""
        prompt = (
            f"Anda adalah AI asisten bisnis untuk seller Warungio Marketplace.\n\n"
            f"Data Toko: {data['store_name']}\n"
            f"Periode: {data['days']} hari terakhir\n\n"
            f"Revenue: Rp {data['current_revenue']:,.0f} ({data['revenue_growth']:+.1f}%)\n"
            f"Pesanan: {data['current_orders']} ({data['order_growth']:+.1f}%)\n"
            f"Produk Aktif: {data['total_products']} (tidak laku: {data['unsold_products']})\n"
            f"Rating: {data['avg_rating']:.1f}/5 ({data['total_reviews']} ulasan)\n"
            f"Pengikut: {data['follower_count']}\n\n"
            "Kembalikan JSON:\n"
            "{\n"
            '  "business_health": "sehat|perlu_perhatian|kritis",\n'
            '  "key_insights": ["Insight 1", "Insight 2", "Insight 3"],\n'
            '  "quick_wins": ["Tindakan cepat 1", "Tindakan cepat 2"],\n'
            '  "strategic_recommendations": [\n'
            '    {"area": "Stok|Harga|Promo|Produk|Pelanggan", "recommendation": "Rekomendasi dalam Bahasa Indonesia", "priority": "high|medium|low"}\n'
            '  ],\n'
            '  "risk_factors": ["Faktor risiko 1", "Faktor risiko 2"],\n'
            '  "growth_opportunities": ["Peluang 1", "Peluang 2"],\n'
            '  "estimated_revenue_forecast": "Proyeksi revenue untuk 30 hari ke depan dalam Bahasa Indonesia",\n'
            '  "summary": "Ringkasan eksekutif 2-3 kalimat dalam Bahasa Indonesia"\n'
            "}"
        )

        result = self.client.generate_structured(
            prompt=prompt,
            temperature=0.4,
            cache_key=f'ai_seller_insights:{self.store.id}:{data["days"]}',
        )

        if not result:
            return {
                'business_health': 'perlu_perhatian',
                'key_insights': ['Pantau data penjualan secara rutin untuk insight lebih akurat.'],
                'summary': 'Analisis AI membutuhkan data yang lebih lengkap. Pantau dashboard secara berkala.',
            }

        return result

    def get_stock_recommendations(self) -> List[Dict]:
        """AI-powered stock recommendations."""
        products = Product.objects.filter(store=self.store, is_active=True)\
            .annotate(
                revenue=Sum('order_items__subtotal', filter=Q(order_items__order__order_status__in=['paid', 'completed', 'shipped', 'processed']))
            ).order_by('-revenue')[:20]

        low_stock = [p for p in products if p.stock and p.stock <= 5]
        out_of_stock = [p for p in products if not p.stock or p.stock == 0]

        recommendations = []
        if low_stock:
            recommendations.append({
                'type': 'restock',
                'priority': 'high',
                'message': f'{len(low_stock)} produk hampir habis. Segera restock.',
                'products': [{'id': p.id, 'name': p.product_name, 'stock': p.stock} for p in low_stock[:5]],
            })
        if out_of_stock:
            recommendations.append({
                'type': 'restock',
                'priority': 'critical',
                'message': f'{len(out_of_stock)} produk sudah habis. Restock segera.',
                'products': [{'id': p.id, 'name': p.product_name} for p in out_of_stock[:5]],
            })

        return recommendations

    def get_promotion_recommendations(self) -> List[Dict]:
        """AI-powered promotion recommendations."""
        products = Product.objects.filter(store=self.store, is_active=True)\
            .annotate(total_sold=Sum('order_items__qty'))\
            .order_by('total_sold')[:10]

        slow_movers = [p for p in products if p.total_sold is None or p.total_sold == 0]

        if not slow_movers:
            return [{'type': 'info', 'message': 'Semua produk memiliki penjualan. Pertahankan!', 'priority': 'low'}]

        return [{
            'type': 'promotion',
            'priority': 'medium',
            'message': f'{len(slow_movers)} produk belum terjual. Buat promo diskon untuk meningkatkan penjualan.',
            'products': [{'id': p.id, 'name': p.product_name, 'price': float(p.price)} for p in slow_movers[:5]],
        }]


def get_seller_assistant(store) -> AISellerAssistant:
    return AISellerAssistant(store)
