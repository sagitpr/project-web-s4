"""
AI Business Insight Service for Warungio Marketplace.
Generates AI-powered business insights, recommendations, and analysis.

Provides actionable insights from sales data, customer behavior, inventory,
and market trends. Designed to power a "Business Intelligence" dashboard.
"""

from datetime import timedelta, date
from decimal import Decimal
from collections import defaultdict

from django.db.models import Sum, Avg, Count, F, Q, Max, Min
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from django.utils import timezone

from orders.models import Order, OrderItem
from products.models import Product, Review, Category
from stores.models import Store, StoreFollower
from accounts.models import User


class BusinessInsightEngine:
    """
    AI-powered business insight generator.
    Analyzes store data and produces actionable recommendations.
    """

    def __init__(self, store):
        self.store = store

    def generate_insights(self, days=30):
        """
        Generate comprehensive business insights for a store.
        
        Returns:
            dict with insights categorized by type
        """
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        prev_start = start_date - timedelta(days=days)
        
        # Gather raw data
        current_period_orders = Order.objects.filter(
            store=self.store,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
        )
        prev_period_orders = Order.objects.filter(
            store=self.store,
            created_at__date__gte=prev_start,
            created_at__date__lt=start_date,
        )
        completed_orders = current_period_orders.filter(
            order_status__in=['paid', 'completed', 'shipped', 'processed']
        )
        prev_completed = prev_period_orders.filter(
            order_status__in=['paid', 'completed', 'shipped', 'processed']
        )

        return {
            'store_id': self.store.id,
            'store_name': self.store.store_name,
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': days,
            },
            'sales_insights': self._sales_insights(completed_orders, prev_completed, start_date, end_date),
            'product_insights': self._product_insights(start_date, end_date),
            'customer_insights': self._customer_insights(start_date, end_date),
            'inventory_insights': self._inventory_insights(),
            'growth_insights': self._growth_insights(completed_orders, prev_completed),
            'recommendations': self._generate_recommendations(completed_orders, start_date, end_date),
            'generated_at': timezone.now().isoformat(),
        }

    def _sales_insights(self, current_orders, prev_orders, start_date, end_date):
        """Analyze sales performance."""
        current_total = current_orders.aggregate(total=Sum('total_price'))['total'] or 0
        prev_total = prev_orders.aggregate(total=Sum('total_price'))['total'] or 0
        current_count = current_orders.count()
        prev_count = prev_orders.count()
        
        # Growth
        sales_growth = ((current_total - prev_total) / prev_total * 100) if prev_total > 0 else 0
        order_growth = ((current_count - prev_count) / prev_count * 100) if prev_count > 0 else 0
        
        # Daily average
        days = max((end_date - start_date).days, 1)
        avg_daily_sales = float(current_total) / days
        avg_daily_orders = current_count / days
        
        # Best day
        daily_sales = current_orders.annotate(
            day=TruncDay('created_at')
        ).values('day').annotate(
            total=Sum('total_price'),
            count=Count('id')
        ).order_by('-total')[:1]
        
        best_day = None
        if daily_sales:
            d = daily_sales[0]
            best_day = {
                'date': d['day'].isoformat() if d['day'] else None,
                'total_sales': float(d['total'] or 0),
                'order_count': d['count'],
            }
        
        # Peak hours
        hourly_data = current_orders.annotate(
            hour=TruncDay('created_at')
        ).values('hour').annotate(
            total=Sum('total_price')
        ).order_by('-total')[:3]
        
        return {
            'total_sales': float(current_total),
            'total_orders': current_count,
            'avg_daily_sales': round(avg_daily_sales, 0),
            'avg_daily_orders': round(avg_daily_orders, 1),
            'sales_growth_percent': round(sales_growth, 1),
            'order_growth_percent': round(order_growth, 1),
            'avg_order_value': float(current_total / current_count) if current_count > 0 else 0,
            'best_day': best_day,
            'summary': self._summarize_sales(sales_growth, current_total, current_count),
        }

    def _product_insights(self, start_date, end_date):
        """Analyze product performance."""
        # Top products
        top_products = OrderItem.objects.filter(
            order__store=self.store,
            order__created_at__date__gte=start_date,
            order__created_at__date__lte=end_date,
            order__order_status__in=['paid', 'completed', 'shipped', 'processed'],
        ).values('product_id', 'product_name').annotate(
            total_sold=Sum('qty'),
            total_revenue=Sum('subtotal'),
        ).order_by('-total_sold')[:10]
        
        # Category breakdown
        category_sales = OrderItem.objects.filter(
            order__store=self.store,
            order__created_at__date__gte=start_date,
            order__created_at__date__lte=end_date,
            order__order_status__in=['paid', 'completed', 'shipped', 'processed'],
        ).values('product__category__category_name').annotate(
            total_sold=Sum('qty'),
            total_revenue=Sum('subtotal'),
        ).order_by('-total_revenue')
        
        # Low performers (products with low sales)
        total_products = Product.objects.filter(store=self.store, is_active=True).count()
        products_with_sales = OrderItem.objects.filter(
            order__store=self.store,
            order__created_at__date__gte=start_date,
        ).values('product_id').distinct().count()
        
        return {
            'top_products': [
                {
                    'product_id': p['product_id'],
                    'product_name': p['product_name'],
                    'total_sold': p['total_sold'],
                    'total_revenue': float(p['total_revenue'] or 0),
                }
                for p in top_products
            ],
            'category_breakdown': [
                {
                    'category': c['product__category__category_name'] or 'Tanpa Kategori',
                    'total_sold': c['total_sold'],
                    'total_revenue': float(c['total_revenue'] or 0),
                }
                for c in category_sales
            ],
            'total_active_products': total_products,
            'products_with_sales': products_with_sales,
            'products_without_sales': total_products - products_with_sales,
            'summary': f'{products_with_sales} dari {total_products} produk aktif memiliki penjualan.',
        }

    def _customer_insights(self, start_date, end_date):
        """Analyze customer behavior."""
        # New vs returning customers
        store_orders = Order.objects.filter(
            store=self.store,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
        ).values('user').annotate(
            order_count=Count('id'),
            total_spent=Sum('total_price'),
            first_order=Min('created_at'),
        )
        
        total_customers = store_orders.count()
        new_customers = sum(1 for o in store_orders 
                           if o['first_order'] and o['first_order'].date() >= start_date)
        returning_customers = total_customers - new_customers
        
        # Top customers
        top_customers = store_orders.order_by('-total_spent')[:10]
        user_ids = [c['user'] for c in top_customers if c['user']]
        users = User.objects.filter(id__in=user_ids) if user_ids else []
        user_map = {u.id: u.full_name or u.email for u in users}
        
        # Followers
        follower_count = StoreFollower.objects.filter(store=self.store).count()
        new_followers = StoreFollower.objects.filter(
            store=self.store,
            created_at__date__gte=start_date,
        ).count()
        
        return {
            'total_customers': total_customers,
            'new_customers': new_customers,
            'returning_customers': returning_customers,
            'return_rate': round(returning_customers / total_customers * 100, 1) if total_customers > 0 else 0,
            'total_followers': follower_count,
            'new_followers': new_followers,
            'top_customers': [
                {
                    'user_id': c['user'],
                    'name': user_map.get(c['user'], 'Anonymous'),
                    'order_count': c['order_count'],
                    'total_spent': float(c['total_spent'] or 0),
                }
                for c in top_customers
            ],
            'summary': f'{new_customers} pelanggan baru, {returning_customers} pelanggan kembali ({returning_customers/total_customers*100:.0f}% retensi).' if total_customers > 0 else 'Belum ada data pelanggan.',
        }

    def _inventory_insights(self):
        """Analyze inventory status."""
        products = Product.objects.filter(store=self.store, is_active=True)
        total_stock = products.aggregate(total=Sum('stock'))['total'] or 0
        
        low_stock = products.filter(stock__lte=5, stock__gt=0).count()
        out_of_stock = products.filter(stock__lte=0).count()
        healthy_stock = products.filter(stock__gt=5).count()
        
        # Stock value
        stock_value = sum(float(p.price) * p.stock for p in products if p.stock > 0)
        
        return {
            'total_products': products.count(),
            'total_stock_units': total_stock,
            'total_stock_value': round(stock_value, 0),
            'healthy_stock': healthy_stock,
            'low_stock': low_stock,
            'out_of_stock': out_of_stock,
            'stock_health_percent': round(healthy_stock / products.count() * 100, 1) if products.count() > 0 else 0,
            'summary': f'{healthy_stock} produk stok sehat, {low_stock} stok rendah, {out_of_stock} habis.',
        }

    def _growth_insights(self, current_orders, prev_orders):
        """Analyze growth trends."""
        current_total = float(current_orders.aggregate(total=Sum('total_price'))['total'] or 0)
        prev_total = float(prev_orders.aggregate(total=Sum('total_price'))['total'] or 0)
        current_count = current_orders.count()
        prev_count = prev_orders.count()
        
        sales_growth = ((current_total - prev_total) / prev_total * 100) if prev_total > 0 else 0
        order_growth = ((current_count - prev_count) / prev_count * 100) if prev_count > 0 else 0
        
        # Determine growth stage
        if sales_growth > 50:
            growth_stage = 'high_growth'
            growth_label = 'Pertumbuhan Tinggi'
        elif sales_growth > 20:
            growth_stage = 'growing'
            growth_label = 'Berkembang'
        elif sales_growth > 0:
            growth_stage = 'stable'
            growth_label = 'Stabil'
        elif sales_growth > -20:
            growth_stage = 'declining'
            growth_label = 'Menurun'
        else:
            growth_stage = 'critical'
            growth_label = 'Kritis'
        
        return {
            'sales_growth_percent': round(sales_growth, 1),
            'order_growth_percent': round(order_growth, 1),
            'growth_stage': growth_stage,
            'growth_label': growth_label,
            'summary': f'{growth_label}: Penjualan {"naik" if sales_growth > 0 else "turun"} {abs(sales_growth):.0f}% dibanding periode sebelumnya.',
        }

    def _generate_recommendations(self, current_orders, start_date, end_date):
        """Generate actionable business recommendations."""
        recommendations = []
        
        # Check stock issues
        low_stock_products = Product.objects.filter(
            store=self.store, is_active=True, stock__lte=5
        ).count()
        out_of_stock_products = Product.objects.filter(
            store=self.store, is_active=True, stock__lte=0
        ).count()
        
        if out_of_stock_products > 0:
            recommendations.append({
                'type': 'inventory',
                'priority': 'critical',
                'title': 'Produk Habis',
                'description': f'{out_of_stock_products} produk kehabisan stok. Segera lakukan restock.',
                'action': 'Restock sekarang',
                'action_url': '/seller/products/?filter=out_of_stock',
            })
        elif low_stock_products > 0:
            recommendations.append({
                'type': 'inventory',
                'priority': 'high',
                'title': 'Stok Menipis',
                'description': f'{low_stock_products} produk memiliki stok rendah (≤5). Segera rencanakan pembelian.',
                'action': 'Lihat produk stok rendah',
                'action_url': '/seller/products/?filter=low_stock',
            })
        
        # Check products without sales
        products_no_sales = Product.objects.filter(
            store=self.store, is_active=True, sold_count=0
        ).count()
        if products_no_sales > 10:
            recommendations.append({
                'type': 'product',
                'priority': 'medium',
                'title': 'Produk Tidak Laku',
                'description': f'{products_no_sales} produk belum pernah terjual. Pertimbangkan promo atau review harga.',
                'action': 'Review produk',
                'action_url': '/seller/products/?filter=no_sales',
            })
        
        # Check reviews
        unreplied_reviews = Review.objects.filter(
            product__store=self.store,
            seller_reply__isnull=True
        ).count()
        if unreplied_reviews > 5:
            recommendations.append({
                'type': 'customer',
                'priority': 'medium',
                'title': 'Ulasan Belum Dibalas',
                'description': f'{unreplied_reviews} ulasan pelanggan belum mendapat balasan. Balas untuk meningkatkan kepercayaan.',
                'action': 'Lihat ulasan',
                'action_url': '/seller/ulasan/',
            })
        
        # Growth recommendations
        total_sales = float(current_orders.aggregate(total=Sum('total_price'))['total'] or 0)
        if total_sales > 10000000:
            recommendations.append({
                'type': 'growth',
                'priority': 'low',
                'title': 'Potensi Ekspansi',
                'description': 'Penjualan Anda sudah bagus! Pertimbangkan menambah varian produk atau buka cabang baru.',
                'action': 'Pelajari ekspansi',
                'action_url': '/seller/partner-guide/',
            })
        
        # Default recommendation
        if not recommendations:
            recommendations.append({
                'type': 'general',
                'priority': 'info',
                'title': 'Semua Terkendali',
                'description': 'Toko Anda dalam kondisi baik. Pantau dashboard secara rutin untuk performa terbaik.',
                'action': 'Lihat dashboard',
                'action_url': '/seller/dashboard/',
            })
        
        return recommendations

    def _summarize_sales(self, growth, total, count):
        """Human-readable sales summary."""
        if total == 0:
            return 'Belum ada penjualan pada periode ini.'
        
        parts = [f'Total penjualan Rp {total:,.0f} dari {count} pesanan.']
        if growth > 0:
            parts.append(f'Naik {growth:.1f}% dibanding periode sebelumnya. 📈')
        elif growth < 0:
            parts.append(f'Turun {abs(growth):.1f}% dibanding periode sebelumnya. 📉')
        else:
            parts.append('Stabil dibanding periode sebelumnya.')
        
        return ' '.join(parts)


class InsightGenerator:
    """
    Quick insight generator for dashboard widgets.
    Produces lightweight insights suitable for real-time display.
    """

    @staticmethod
    def quick_insights(store):
        """Get quick overview insights."""
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        
        today_orders = Order.objects.filter(
            store=store,
            created_at__date=today,
        )
        week_orders = Order.objects.filter(
            store=store,
            created_at__date__gte=week_ago,
        )
        
        return {
            'quick_stats': {
                'today_revenue': float(today_orders.aggregate(total=Sum('total_price'))['total'] or 0),
                'today_orders': today_orders.count(),
                'week_revenue': float(week_orders.aggregate(total=Sum('total_price'))['total'] or 0),
                'week_orders': week_orders.count(),
                'total_products': Product.objects.filter(store=store, is_active=True).count(),
                'total_followers': StoreFollower.objects.filter(store=store).count(),
            },
            'alerts': InsightGenerator._get_alerts(store),
        }

    @staticmethod
    def _get_alerts(store):
        """Get active alerts for the store."""
        alerts = []
        
        # Low stock alerts
        low_stock = Product.objects.filter(store=store, is_active=True, stock__lte=5, stock__gt=0).count()
        if low_stock > 0:
            alerts.append({
                'type': 'warning',
                'message': f'{low_stock} produk stok rendah',
                'count': low_stock,
            })
        
        # Out of stock
        out_of_stock = Product.objects.filter(store=store, is_active=True, stock__lte=0).count()
        if out_of_stock > 0:
            alerts.append({
                'type': 'danger',
                'message': f'{out_of_stock} produk habis',
                'count': out_of_stock,
            })
        
        # Pending orders
        pending = Order.objects.filter(store=store, order_status='pending').count()
        if pending > 0:
            alerts.append({
                'type': 'info',
                'message': f'{pending} pesanan menunggu konfirmasi',
                'count': pending,
            })
        
        return alerts
