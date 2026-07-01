"""
AI Business Insight Service for Warungio Marketplace.
Integrated into the analytics app for seller insights.
"""

from datetime import timedelta
from django.db.models import Sum, Avg, Count
from django.utils import timezone

from orders.models import Order, OrderItem
from products.models import Product, Review
from stores.models import StoreFollower


class AISellerInsightService:
    """
    AI-powered business insight generator for sellers.
    """

    def __init__(self, store):
        self.store = store

    def get_comprehensive_insights(self, days=30):
        """Generate comprehensive business insights."""
        from products.services.ai_insight import BusinessInsightEngine
        engine = BusinessInsightEngine(self.store)
        return engine.generate_insights(days)

    def get_quick_insights(self):
        """Get quick dashboard insights."""
        from products.services.ai_insight import InsightGenerator
        return InsightGenerator.quick_insights(self.store)

    def get_growth_tips(self):
        """Generate actionable growth tips."""
        today = timezone.now().date()
        month_start = today - timedelta(days=30)
        prev_start = month_start - timedelta(days=30)

        current_orders = Order.objects.filter(
            store=self.store,
            created_at__date__gte=month_start,
            order_status__in=['paid', 'completed', 'shipped', 'processed']
        )
        prev_orders = Order.objects.filter(
            store=self.store,
            created_at__date__gte=prev_start,
            created_at__date__lt=month_start,
            order_status__in=['paid', 'completed', 'shipped', 'processed']
        )

        current_total = float(current_orders.aggregate(total=Sum('total_price'))['total'] or 0)
        prev_total = float(prev_orders.aggregate(total=Sum('total_price'))['total'] or 0)
        growth = ((current_total - prev_total) / prev_total * 100) if prev_total > 0 else 0

        tips = []
        if growth < 0:
            tips.append({
                'type': 'growth',
                'priority': 'high',
                'title': 'Penjualan Menurun',
                'tip': 'Coba aktifkan promo diskon atau gratis ongkir untuk meningkatkan penjualan.',
                'action': 'Buat Promo',
                'action_url': '/seller/promo-diskon/',
            })
        if growth > 50:
            tips.append({
                'type': 'growth',
                'priority': 'medium',
                'title': 'Pertumbuhan Tinggi!',
                'tip': 'Pertimbangkan menambah stok produk terlaris dan memperluas jangkauan pengiriman.',
                'action': 'Lihat Stok',
                'action_url': '/seller/products/',
            })

        tips.append({
            'type': 'general',
            'priority': 'info',
            'title': 'Tips Bisnis',
            'tip': 'Produk dengan foto berkualitas tinggi memiliki 30% lebih banyak peluang terjual.',
            'action': 'Update Produk',
            'action_url': '/seller/products/',
        })

        return {
            'growth_percent': round(growth, 1),
            'tips': tips,
            'generated_at': timezone.now().isoformat(),
        }
