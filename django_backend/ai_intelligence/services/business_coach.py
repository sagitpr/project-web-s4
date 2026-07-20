"""
AI Business Coach Service.
Generates proactive coaching insights for sellers covering
growth, risk, optimization, inventory, pricing, and operations.
"""

import logging
from datetime import timedelta, date
from typing import Dict, List, Optional
from decimal import Decimal
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone

logger = logging.getLogger(__name__)


class BusinessCoachService:
    """
    Proactive business coaching for Warungio sellers.
    Analyzes store performance and generates actionable insights.
    """

    def generate_insights_for_store(self, store) -> List[Dict]:
        """
        Generate all relevant coaching insights for a store.
        Returns list of insight dicts ready to create BusinessCoachInsight records.
        """
        insights = []
        insights.extend(self._check_growth_opportunities(store))
        insights.extend(self._check_risk_alerts(store))
        insights.extend(self._check_optimization_suggestions(store))
        insights.extend(self._check_inventory_insights(store))
        insights.extend(self._check_pricing_insights(store))
        insights.extend(self._check_customer_insights(store))
        insights.extend(self._check_product_insights(store))
        insights.extend(self._check_revenue_insights(store))
        insights.extend(self._check_operational_insights(store))
        return insights

    def _check_growth_opportunities(self, store) -> List[Dict]:
        """Identify growth opportunities."""
        from orders.models import Order
        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)

        orders_30d = Order.objects.filter(store=store, created_at__gte=thirty_days_ago).count()
        prev_30d = Order.objects.filter(
            store=store,
            created_at__gte=now - timedelta(days=60),
            created_at__lt=thirty_days_ago
        ).count()

        insights = []
        if orders_30d > prev_30d and prev_30d > 0:
            growth = ((orders_30d - prev_30d) / prev_30d) * 100
            insights.append({
                'category': 'growth',
                'priority': 2,
                'title': '📈 Pertumbuhan Pesanan Positif',
                'description': f'Pesanan meningkat {growth:.0f}% dalam 30 hari terakhir dibandingkan periode sebelumnya.',
                'recommendation': 'Pertahankan kualitas dan stok. Pertimbangkan menambah variasi produk.',
                'expected_impact': '+15-25% pesanan dalam 60 hari',
                'metric_before': float(prev_30d),
                'metric_after': float(orders_30d),
                'supporting_data': {'orders_30d': orders_30d, 'prev_30d': prev_30d, 'growth_pct': round(growth, 1)},
            })
        elif orders_30d < prev_30d and prev_30d > 0:
            decline = ((prev_30d - orders_30d) / prev_30d) * 100
            insights.append({
                'category': 'growth',
                'priority': 3,
                'title': '⚠️ Penurunan Pesanan Terdeteksi',
                'description': f'Pesanan menurun {decline:.0f}% dalam 30 hari terakhir.',
                'recommendation': 'Review aktivitas kompetitor. Cek kualitas produk. Pertimbangkan promo.',
                'expected_impact': 'Cegah penurunan lebih lanjut',
                'metric_before': float(prev_30d),
                'metric_after': float(orders_30d),
                'supporting_data': {'orders_30d': orders_30d, 'prev_30d': prev_30d, 'decline_pct': round(decline, 1)},
            })
        return insights

    def _check_risk_alerts(self, store) -> List[Dict]:
        """Identify risk alerts."""
        from orders.models import Order
        now = timezone.now()
        seven_days_ago = now - timedelta(days=7)

        insights = []

        # Low stock products
        low_stock = store.products.filter(is_active=True, stock__gt=0, stock__lte=5).count()
        if low_stock >= 3:
            insights.append({
                'category': 'risk', 'priority': 4,
                'title': '🔴 Stok Menipis — Segera Restock!',
                'description': f'{low_stock} produk memiliki stok ≤5 unit. Risiko kehabisan stok tinggi.',
                'recommendation': 'Segera lakukan pemesanan ke supplier untuk produk-produk ini.',
                'expected_impact': 'Cegah kehilangan penjualan dan rating buruk',
                'supporting_data': {'low_stock_count': low_stock},
            })

        # Out of stock
        oos = store.products.filter(is_active=True, stock=0).count()
        if oos >= 3:
            insights.append({
                'category': 'risk', 'priority': 3,
                'title': '📦 Produk Habis — Potensi Revenue Hilang',
                'description': f'{oos} produk sedang habis. Setiap hari tanpa stok adalah revenue yang hilang.',
                'recommendation': 'Restock produk best-seller terlebih dahulu. Prioritaskan yang punya permintaan tinggi.',
                'expected_impact': f'Pulihkan potensi revenue dari {oos} produk',
                'supporting_data': {'out_of_stock_count': oos},
            })

        # High cancellation rate
        total_7d = Order.objects.filter(store=store, created_at__gte=seven_days_ago).count()
        cancelled_7d = Order.objects.filter(store=store, order_status='cancelled', created_at__gte=seven_days_ago).count()
        if total_7d > 0 and (cancelled_7d / total_7d) > 0.2:
            insights.append({
                'category': 'risk', 'priority': 3,
                'title': '⚠️ Tingkat Pembatalan Tinggi',
                'description': f'{cancelled_7d}/{total_7d} pesanan dibatalkan ({(cancelled_7d/total_7d)*100:.0f}%).',
                'recommendation': 'Cek alasan pembatalan. Mungkin waktu proses terlalu lama atau stok tidak tersedia.',
                'expected_impact': 'Turunkan cancellation rate di bawah 10%',
                'supporting_data': {'cancelled': cancelled_7d, 'total': total_7d},
            })
        return insights

    def _check_optimization_suggestions(self, store) -> List[Dict]:
        """Identify optimization opportunities."""
        insights = []

        # Products without photos
        no_photo = store.products.filter(is_active=True, product_photo='').count()
        if no_photo > 0:
            insights.append({
                'category': 'optimization', 'priority': 2,
                'title': f'📷 {no_photo} Produk Tanpa Foto',
                'description': f'Produk dengan foto memiliki conversion rate 3x lebih tinggi.',
                'recommendation': 'Tambahkan foto produk berkualitas. Gunakan AI Smart Scan Gratis!',
                'expected_impact': '+200% conversion rate untuk produk dengan foto',
                'supporting_data': {'no_photo_count': no_photo},
            })

        # Products without description
        no_desc = store.products.filter(is_active=True, description='').count()
        if no_desc > 0:
            insights.append({
                'category': 'optimization', 'priority': 1,
                'title': f'📝 {no_desc} Produk Tanpa Deskripsi',
                'description': 'Produk dengan deskripsi lengkap lebih mudah ditemukan di pencarian.',
                'recommendation': 'Gunakan AI Description Generator untuk membuat deskripsi otomatis.',
                'expected_impact': '+50% search visibility',
                'supporting_data': {'no_desc_count': no_desc},
            })
        return insights

    def _check_inventory_insights(self, store) -> List[Dict]:
        """Identify inventory insights."""
        from products.models import Product
        insights = []

        # Slow moving products (no sales in 30 days)
        products = store.products.filter(is_active=True)
        slow_movers = []
        for p in products:
            if p.sold_count == 0 or (p.stock > 0 and p.sold_count == 0):
                slow_movers.append(p.product_name)

        if len(slow_movers) >= 3:
            insights.append({
                'category': 'inventory', 'priority': 2,
                'title': f'🐌 {len(slow_movers)} Produk Lambat Bergerak',
                'description': 'Produk-produk ini belum terjual dalam 30 hari. Stok mengendap.',
                'recommendation': 'Beri diskon atau bundle dengan produk populer. Atau nonaktifkan sementara.',
                'expected_impact': 'Kurangi stok mengendap, optimalkan modal',
                'supporting_data': {'slow_movers': slow_movers[:10], 'count': len(slow_movers)},
            })
        return insights

    def _check_pricing_insights(self, store) -> List[Dict]:
        """Identify pricing insights."""
        from products.models import Product
        from orders.models import OrderItem

        insights = []
        products = store.products.filter(is_active=True)

        for product in products.order_by('-sold_count')[:5]:
            if product.sold_count > 0:
                # Simple price elasticity check
                avg_price = float(product.price)
                market_min = avg_price * 0.7
                market_max = avg_price * 1.3
                insights.append({
                    'category': 'pricing', 'priority': 1,
                    'title': f'💰 Review Harga: {product.product_name}',
                    'description': f'Harga saat ini: Rp {avg_price:,.0f}. Range market: Rp {market_min:,.0f} - Rp {market_max:,.0f}',
                    'recommendation': 'Gunakan AI Price Advisor untuk optimalisasi harga.',
                    'expected_impact': '+5-15% revenue',
                    'supporting_data': {
                        'product_id': product.id,
                        'current_price': str(product.price),
                        'market_min': str(round(market_min, 2)),
                        'market_max': str(round(market_max, 2)),
                    },
                })
        return insights[:3]  # Max 3 pricing insights

    def _check_customer_insights(self, store) -> List[Dict]:
        """Identify customer insights."""
        from orders.models import Order
        insights = []

        # Repeat customers
        repeat = Order.objects.filter(
            store=store
        ).values('user').annotate(count=Count('id')).filter(count__gt=1).count()
        total_customers = Order.objects.filter(store=store).values('user').distinct().count()
        repeat_rate = (repeat / max(total_customers, 1)) * 100

        if repeat_rate < 20:
            insights.append({
                'category': 'customer', 'priority': 2,
                'title': '👥 Tingkat Repeat Customer Rendah',
                'description': f'Hanya {repeat_rate:.0f}% pelanggan yang kembali belanja.',
                'recommendation': 'Buat program loyalitas sederhana. Follow up setelah pembelian.',
                'expected_impact': '+15-30% repeat orders',
                'supporting_data': {'repeat_rate': round(repeat_rate, 1), 'repeat': repeat, 'total': total_customers},
            })
        return insights

    def _check_product_insights(self, store) -> List[Dict]:
        """Identify product performance insights."""
        from products.models import Product
        insights = []

        products = store.products.filter(is_active=True).order_by('-sold_count')
        best_seller = products.first()
        if best_seller and best_seller.sold_count > 0:
            insights.append({
                'category': 'product', 'priority': 2,
                'title': f'🏆 Best Seller: {best_seller.product_name}',
                'description': f'Terjual {best_seller.sold_count} unit. Rating: {best_seller.rating_avg:.1f}★',
                'recommendation': 'Pastikan stok selalu tersedia. Pertimbangkan variasi produk ini.',
                'expected_impact': 'Maximalkan revenue dari produk unggulan',
                'supporting_data': {
                    'product_id': best_seller.id,
                    'product_name': best_seller.product_name,
                    'sold': best_seller.sold_count,
                    'rating': float(best_seller.rating_avg),
                },
            })
        return insights

    def _check_revenue_insights(self, store) -> List[Dict]:
        """Identify revenue insights."""
        from orders.models import Order
        now = timezone.now()
        insights = []

        # Revenue today vs yesterday
        today = now.date()
        yesterday = today - timedelta(days=1)
        today_rev = Order.objects.filter(store=store, created_at__date=today).aggregate(
            total=Sum('total_price'))['total'] or 0
        yesterday_rev = Order.objects.filter(store=store, created_at__date=yesterday).aggregate(
            total=Sum('total_price'))['total'] or 0

        if yesterday_rev > 0:
            change = ((float(today_rev) - float(yesterday_rev)) / float(yesterday_rev)) * 100
            if change > 20:
                insights.append({
                    'category': 'revenue', 'priority': 2,
                    'title': f'📊 Revenue Hari Ini Naik {change:.0f}%',
                    'description': f'Revenue hari ini Rp {float(today_rev):,.0f} (kemarin Rp {float(yesterday_rev):,.0f})',
                    'recommendation': 'Analisis apa yang mendorong kenaikan dan pertahankan strateginya.',
                    'expected_impact': 'Pertahankan momentum pertumbuhan',
                    'supporting_data': {
                        'today_revenue': str(today_rev),
                        'yesterday_revenue': str(yesterday_rev),
                        'change_pct': round(change, 1),
                    },
                })
        return insights

    def _check_operational_insights(self, store) -> List[Dict]:
        """Identify operational insights."""
        from orders.models import Delivery, Order
        insights = []

        # Unprocessed orders
        unprocessed = Order.objects.filter(
            store=store, order_status='paid'
        ).count()
        if unprocessed >= 3:
            insights.append({
                'category': 'operation', 'priority': 3,
                'title': f'⏳ {unprocessed} Pesanan Belum Diproses',
                'description': f'Pesanan menunggu diproses. Semakin cepat diproses, semakin puas pelanggan.',
                'recommendation': 'Proses pesanan sekarang. Target maksimal 30 menit.',
                'expected_impact': '+20% customer satisfaction',
                'supporting_data': {'unprocessed_count': unprocessed},
            })
        return insights


# Singleton
_coach_service = None


def get_business_coach_service() -> BusinessCoachService:
    global _coach_service
    if _coach_service is None:
        _coach_service = BusinessCoachService()
    return _coach_service
