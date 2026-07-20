"""
AI Dashboard Insights.
Generates summaries, trends, forecasts, and actionable business recommendations
for sellers and administrators using Gemini API.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import timedelta
from django.db.models import Sum, Avg, Count, Q
from django.utils import timezone
from django.core.cache import cache

from orders.models import Order, OrderItem
from products.models import Product, Review, Category
from stores.models import Store, StoreFollower
from accounts.models import User
from .gemini_client import get_gemini_client

logger = logging.getLogger('django_backend.ai_services.dashboard')


class AIDashboardInsights:
    """
    AI-powered dashboard insights.
    
    For Sellers:
    - Revenue trends and forecasts
    - Product performance analysis
    - Customer behavior insights
    - Growth opportunities
    
    For Admins:
    - Platform-wide metrics
    - Market trends
    - Anomaly detection
    """

    def __init__(self):
        self.client = get_gemini_client()

    def seller_dashboard_insights(self, store, days: int = 30) -> Dict[str, Any]:
        """Generate comprehensive dashboard insights for a seller."""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        prev_start = start_date - timedelta(days=days)

        # Gather metrics
        current_orders = Order.objects.filter(
            store=store,
            created_at__date__gte=start_date,
        )
        prev_orders = Order.objects.filter(
            store=store,
            created_at__date__gte=prev_start,
            created_at__date__lt=start_date,
        )

        current_revenue = current_orders.aggregate(t=Sum('total_price'))['t'] or 0
        prev_revenue = prev_orders.aggregate(t=Sum('total_price'))['t'] or 0
        revenue_change = ((current_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0

        current_count = current_orders.count()
        prev_count = prev_orders.count()
        order_change = ((current_count - prev_count) / prev_count * 100) if prev_count > 0 else 0

        # Product metrics
        total_products = Product.objects.filter(store=store, is_active=True).count()
        out_of_stock = Product.objects.filter(store=store, is_active=True, stock=0).count()
        low_stock = Product.objects.filter(store=store, is_active=True, stock__gt=0, stock__lte=5).count()

        # Customer metrics
        total_followers = StoreFollower.objects.filter(store=store).count()
        avg_rating = Review.objects.filter(product__store=store).aggregate(avg=Avg('rating'))['avg'] or 0

        # Generate AI narrative
        ai_narrative = self._generate_seller_narrative(
            store_name=store.store_name,
            revenue=current_revenue,
            revenue_change=revenue_change,
            orders=current_count,
            order_change=order_change,
            total_products=total_products,
            out_of_stock=out_of_stock,
            low_stock=low_stock,
            followers=total_followers,
            rating=avg_rating,
            days=days,
        )

        return {
            'store_id': store.id,
            'store_name': store.store_name,
            'period_days': days,
            'metrics': {
                'revenue': float(current_revenue),
                'revenue_change_percent': round(revenue_change, 1),
                'orders': current_count,
                'order_change_percent': round(order_change, 1),
                'avg_order_value': float(current_revenue / current_count) if current_count > 0 else 0,
                'total_products': total_products,
                'out_of_stock': out_of_stock,
                'low_stock': low_stock,
                'stock_health_percent': round((total_products - out_of_stock - low_stock) / max(total_products, 1) * 100, 1),
                'followers': total_followers,
                'avg_rating': round(float(avg_rating), 2),
                'new_customers': current_orders.values('user').distinct().count(),
            },
            'ai_narrative': ai_narrative,
            'generated_at': timezone.now().isoformat(),
        }

    def admin_dashboard_insights(self, days: int = 30) -> Dict[str, Any]:
        """Generate platform-wide insights for administrators."""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        # Platform metrics
        total_stores = Store.objects.count()
        active_stores = Store.objects.filter(status='active').count()
        total_users = User.objects.filter(is_active=True).count()
        total_sellers = User.objects.filter(is_active=True, role='seller').count()
        total_buyers = User.objects.filter(is_active=True, role='buyer').count()

        new_users_30d = User.objects.filter(
            is_active=True,
            date_joined__gte=start_date,
        ).count()

        total_orders = Order.objects.filter(
            created_at__date__gte=start_date,
        ).count()
        total_revenue = Order.objects.filter(
            created_at__date__gte=start_date,
            order_status__in=['paid', 'completed', 'shipped', 'processed'],
        ).aggregate(t=Sum('total_price'))['t'] or 0

        total_products = Product.objects.filter(is_active=True).count()

        # AI narrative
        ai_narrative = self._generate_admin_narrative(
            stores=total_stores,
            active_stores=active_stores,
            users=total_users,
            sellers=total_sellers,
            buyers=total_buyers,
            new_users=new_users_30d,
            orders=total_orders,
            revenue=total_revenue,
            products=total_products,
            days=days,
        )

        return {
            'period_days': days,
            'metrics': {
                'total_stores': total_stores,
                'active_stores': active_stores,
                'total_users': total_users,
                'total_sellers': total_sellers,
                'total_buyers': total_buyers,
                'new_users_30d': new_users_30d,
                'total_orders': total_orders,
                'total_revenue': float(total_revenue),
                'total_products': total_products,
                'conversion_rate': round(total_orders / max(total_users, 1) * 100, 2),
            },
            'ai_narrative': ai_narrative,
            'generated_at': timezone.now().isoformat(),
        }

    def _generate_seller_narrative(self, **data) -> Dict[str, Any]:
        """Use Gemini to generate narrative insights for seller dashboard."""
        prompt = (
            f"Anda adalah AI analis bisnis untuk seller Warungio Marketplace.\n"
            f"Buat ringkasan dashboard yang informatif.\n\n"
            f"Toko: {data['store_name']}\n"
            f"Periode: {data['days']} hari\n\n"
            f"Revenue: Rp {data['revenue']:,.0f} ({data['revenue_change']:+.1f}%)\n"
            f"Pesanan: {data['orders']} ({data['order_change']:+.1f}%)\n"
            f"Produk: {data['total_products']} total, {data['out_of_stock']} habis, {data['low_stock']} hampir habis\n"
            f"Pengikut: {data['followers']}\n"
            f"Rating: {data['rating']:.1f}/5\n\n"
            "Kembalikan JSON:\n"
            "{\n"
            '  "headline": "1 kalimat headline menarik dalam Bahasa Indonesia",\n'
            '  "summary": "Ringkasan performa 2-3 kalimat",\n'
            '  "key_highlight": "Highlight terpenting periode ini",\n'
            '  "areas_needing_attention": ["Area 1", "Area 2"],\n'
            '  "forecast": "Proyeksi 7 hari ke depan",\n'
            '  "confidence": 0.0-1.0\n'
            "}"
        )

        result = self.client.generate_structured(
            prompt=prompt,
            temperature=0.4,
            cache_key=f'ai_dash_seller:{data["store_name"]}:{data["days"]}',
        )

        return result or {
            'headline': 'Dashboard siap dengan data terkini.',
            'summary': 'Pantau metrik toko Anda secara berkala.',
            'key_highlight': 'Data telah diperbarui.',
            'areas_needing_attention': [],
            'forecast': 'Gunakan data historis untuk proyeksi.',
            'confidence': 0.5,
        }

    def _generate_admin_narrative(self, **data) -> Dict[str, Any]:
        """Use Gemini to generate platform-wide narrative for admin dashboard."""
        prompt = (
            f"Anda adalah AI analis untuk admin Warungio Marketplace.\n"
            f"Buat ringkasan platform.\n\n"
            f"Periode: {data['days']} hari\n\n"
            f"Toko: {data['stores']} total, {data['active_stores']} aktif\n"
            f"Pengguna: {data['users']} total ({data['sellers']} seller, {data['buyers']} buyer)\n"
            f"Pendaftar Baru: {data['new_users']}\n"
            f"Pesanan: {data['orders']}\n"
            f"Revenue: Rp {data['revenue']:,.0f}\n"
            f"Produk: {data['products']}\n\n"
            "Kembalikan JSON:\n"
            "{\n"
            '  "headline": "Headline platform dalam Bahasa Indonesia",\n'
            '  "summary": "Ringkasan performa platform",\n'
            '  "key_metrics_insight": "Insight dari metrik utama",\n'
            '  "growth_indicators": ["Indikator 1", "Indikator 2"],\n'
            '  "action_items": ["Tindakan 1", "Tindakan 2"]\n'
            "}"
        )

        result = self.client.generate_structured(
            prompt=prompt,
            temperature=0.4,
        )

        return result or {'summary': 'Dashboard admin siap.', 'action_items': []}


def get_dashboard_insights() -> AIDashboardInsights:
    return AIDashboardInsights()
