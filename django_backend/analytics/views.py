"""
Analytics views for Warungio Marketplace.
Real-time seller dashboard analytics.
"""

from django.db.models import Sum, Count, Avg, Q, Min
from django.db.models.functions import TruncDate, TruncMonth, TruncDay
from django.utils import timezone
from datetime import timedelta, date, datetime
from decimal import Decimal
from rest_framework import status, generics, permissions, views
from rest_framework.response import Response

from .models import SalesAnalytics, DeviceAnalytics, UserActivity, DailyReport
from .serializers import (
    SalesAnalyticsSerializer, SalesSummarySerializer, SalesTrendSerializer,
    DeviceAnalyticsSerializer, DeviceBreakdownSerializer,
    UserActivitySerializer, DashboardStatsSerializer
)
from orders.models import Order, OrderItem
from products.models import Product, Review
from stores.models import StoreFollower
from accounts.permissions import IsSeller, IsAdmin
from .services.ai_insight import AISellerInsightService


class DashboardSummaryView(views.APIView):
    """Get seller dashboard summary statistics."""
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get(self, request):
        store = request.user.store
        period = request.query_params.get('period', 'month')  # week, month, year
        
        # Calculate date range
        today = timezone.now().date()
        if period == 'week':
            start_date = today - timedelta(days=7)
        elif period == 'month':
            start_date = today - timedelta(days=30)
        elif period == 'year':
            start_date = today - timedelta(days=365)
        else:
            start_date = today - timedelta(days=30)
        
        # Orders in period (completed/paid)
        orders_qs = Order.objects.filter(
            store=store,
            created_at__date__gte=start_date,
            order_status__in=['paid', 'processed', 'shipped', 'completed']
        )
        
        # Calculate stats
        total_sales = orders_qs.aggregate(
            total=Sum('total_price')
        )['total'] or 0
        
        total_orders = orders_qs.count()
        
        # Products sold
        products_sold = OrderItem.objects.filter(
            order__in=orders_qs
        ).aggregate(total=Sum('qty'))['total'] or 0
        
        # New customers (store followers in period)
        new_customers = StoreFollower.objects.filter(
            store=store,
            created_at__date__gte=start_date
        ).count()
        
        # Total followers
        total_followers = StoreFollower.objects.filter(store=store).count()
        
        # Average rating
        avg_rating = Review.objects.filter(
            product__store=store
        ).aggregate(avg=Avg('rating'))['avg'] or 0
        
        # Total products
        total_products = Product.objects.filter(store=store, is_active=True).count()
        
        # Pending orders
        pending_orders = Order.objects.filter(
            store=store, order_status='pending'
        ).count()
        
        # Sales trend data
        sales_data = self._get_sales_trend(store, start_date, today)
        
        # Device breakdown
        device_data = self._get_device_breakdown(store, start_date)
        
        # Recent orders
        recent_orders = self._get_recent_orders(store)
        
        # Top products
        top_products = self._get_top_products(store, start_date)
        
        data = {
            'total_sales': total_sales,
            'total_orders': total_orders,
            'products_sold': products_sold,
            'new_customers': new_customers,
            'total_followers': total_followers,
            'average_rating': round(avg_rating, 2),
            'total_products': total_products,
            'pending_orders': pending_orders,
            'sales_chart': sales_data,
            'device_breakdown': device_data,
            'recent_orders': recent_orders,
            'top_products': top_products,
        }
        
        return Response(data)

    def _get_sales_trend(self, store, start_date, end_date):
        """Get daily sales data for charts."""
        orders = Order.objects.filter(
            store=store,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            order_status__in=['paid', 'processed', 'shipped', 'completed']
        ).annotate(
            day=TruncDay('created_at')
        ).values('day').annotate(
            daily_sales=Sum('total_price'),
            daily_orders=Count('id')
        ).order_by('day')
        
        # Build chart data
        days = []
        sales = []
        order_counts = []
        
        current = start_date
        while current <= end_date:
            days.append(current.strftime('%d %b'))
            found = [o for o in orders if o['day'] and o['day'].date() == current]
            if found:
                sales.append(float(found[0]['daily_sales']))
                order_counts.append(found[0]['daily_orders'])
            else:
                sales.append(0)
                order_counts.append(0)
            current += timedelta(days=1)
        
        return {
            'labels': days,
            'daily_sales': sales,
            'daily_orders': order_counts,
            'daily_customers': [],
        }

    def _get_device_breakdown(self, store, start_date):
        """Get device usage breakdown."""
        activities = UserActivity.objects.filter(
            store=store,
            created_at__date__gte=start_date
        )
        
        mobile = activities.filter(device_type='mobile').count()
        tablet = activities.filter(device_type='tablet').count()
        desktop = activities.filter(device_type='desktop').count()
        total = mobile + tablet + desktop or 1
        
        return {
            'mobile_percentage': round(mobile / total * 100, 2),
            'tablet_percentage': round(tablet / total * 100, 2),
            'desktop_percentage': round(desktop / total * 100, 2),
            'mobile_count': mobile,
            'tablet_count': tablet,
            'desktop_count': desktop,
        }

    def _get_recent_orders(self, store, limit=10):
        """Get recent orders for dashboard."""
        orders = Order.objects.filter(store=store).select_related(
            'user'
        ).order_by('-created_at')[:limit]
        
        return [{
            'id': o.id,
            'order_number': o.order_number,
            'customer_name': o.user.full_name if o.user else 'Anonymous',
            'total_price': float(o.total_price),
            'order_status': o.order_status,
            'created_at': o.created_at,
        } for o in orders]

    def _get_top_products(self, store, start_date, limit=5):
        """Get top selling products."""
        items = OrderItem.objects.filter(
            order__store=store,
            order__created_at__date__gte=start_date,
            order__order_status__in=['paid', 'processed', 'shipped', 'completed']
        ).values('product_id', 'product_name').annotate(
            total_sold=Sum('qty'),
            total_revenue=Sum('subtotal')
        ).order_by('-total_sold')[:limit]
        
        return [{
            'product_id': i['product_id'],
            'product_name': i['product_name'],
            'total_sold': i['total_sold'],
            'total_revenue': float(i['total_revenue']),
        } for i in items]


class SalesAnalyticsView(generics.ListAPIView):
    """Get detailed sales analytics."""
    serializer_class = SalesAnalyticsSerializer
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get_queryset(self):
        store = self.request.user.store
        return SalesAnalytics.objects.filter(store=store).order_by('-date')


class SalesTrendDataView(views.APIView):
    """Get sales trend data for charts."""
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get(self, request):
        store = request.user.store
        period = request.query_params.get('period', '30')
        days = int(period)
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        orders = Order.objects.filter(
            store=store,
            created_at__date__gte=start_date,
            order_status__in=['paid', 'completed']
        ).annotate(
            day=TruncDay('created_at')
        ).values('day').annotate(
            total=Sum('total_price'),
            count=Count('id')
        ).order_by('day')
        
        labels = []
        sales = []
        order_counts = []
        
        current = start_date
        while current <= end_date:
            labels.append(current.strftime('%d %b'))
            found = [o for o in orders if o['day'] and o['day'].date() == current]
            if found:
                sales.append(float(found[0]['total']))
                order_counts.append(found[0]['count'])
            else:
                sales.append(0)
                order_counts.append(0)
            current += timedelta(days=1)
        
        return Response({
            'labels': labels,
            'daily_sales': sales,
            'daily_orders': order_counts,
        })


class DeviceAnalyticsView(views.APIView):
    """Get device usage analytics."""
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get(self, request):
        store = request.user.store
        period = request.query_params.get('period', '30')
        days = int(period)
        
        start_date = timezone.now().date() - timedelta(days=days)
        
        activities = UserActivity.objects.filter(
            store=store,
            created_at__date__gte=start_date
        )
        
        mobile = activities.filter(device_type='mobile').count()
        tablet = activities.filter(device_type='tablet').count()
        desktop = activities.filter(device_type='desktop').count()
        
        # Browser breakdown
        browsers = activities.values('device_type').annotate(
            count=Count('id')
        )
        
        return Response({
            'mobile': mobile,
            'tablet': tablet,
            'desktop': desktop,
            'total': mobile + tablet + desktop,
            'breakdown': [
                {'device': b['device_type'], 'count': b['count']}
                for b in browsers
            ],
        })


class UserActivityView(generics.ListAPIView):
    """Get recent user activities."""
    serializer_class = UserActivitySerializer
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get_queryset(self):
        store = self.request.user.store
        return UserActivity.objects.filter(store=store).select_related(
            'user'
        ).order_by('-created_at')[:50]


class DailyReportView(generics.ListAPIView):
    """Get daily reports."""
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get_queryset(self):
        store = self.request.user.store
        return DailyReport.objects.filter(store=store).order_by('-date')


class RealTimeAnalyticsView(views.APIView):
    """Get real-time analytics for WebSocket fallback."""
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get(self, request):
        store = request.user.store
        today = timezone.now().date()
        
        today_orders = Order.objects.filter(
            store=store,
            created_at__date=today,
            order_status__in=['paid', 'processed', 'shipped', 'completed']
        )
        
        return Response({
            'today_sales': float(today_orders.aggregate(total=Sum('total_price'))['total'] or 0),
            'today_orders': today_orders.count(),
            'today_visitors': UserActivity.objects.filter(
                store=store,
                created_at__date=today,
                activity_type='page_view'
            ).count(),
            'pending_orders': Order.objects.filter(
                store=store, order_status='pending'
            ).count(),
        })

# =============================================================================
# AI BUSINESS INSIGHT
# =============================================================================


class AIBusinessInsightView(views.APIView):
    """Get AI-powered business insights for seller.

    Returns comprehensive analysis including:
    - Sales insights with growth trends
    - Product performance analysis
    - Customer behavior insights
    - Inventory health check
    - Actionable recommendations

    Flutter-ready JSON response.
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get(self, request):
        days = int(request.query_params.get('days', 30))
        service = AISellerInsightService(request.user.store)
        insights = service.get_comprehensive_insights(days)
        return Response(insights)


class AIQuickInsightView(views.APIView):
    """Get quick dashboard insights."""
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get(self, request):
        service = AISellerInsightService(request.user.store)
        insights = service.get_quick_insights()
        return Response(insights)


class AIGrowthTipsView(views.APIView):
    """Get AI-generated growth tips."""
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get(self, request):
        service = AISellerInsightService(request.user.store)
        tips = service.get_growth_tips()
        return Response(tips)


class AdminAIBusinessOverviewView(views.APIView):
    """Admin overview of all AI business insights."""
    permission_classes = (permissions.IsAuthenticated, IsAdmin)

    def get(self, request):
        from stores.models import Store
        stores = Store.objects.filter(status='active')[:10]
        all_insights = []
        for store in stores:
            try:
                service = AISellerInsightService(store)
                quick = service.get_quick_insights()
                all_insights.append({
                    'store_id': store.id,
                    'store_name': store.store_name,
                    'quick_stats': quick.get('quick_stats', {}),
                    'alerts': quick.get('alerts', []),
                })
            except Exception:
                pass
        return Response({
            'stores_analyzed': len(all_insights),
            'insights': all_insights,
        })


class MockAIBusinessInsightView(views.APIView):
    """Mock AI insight data for Flutter development."""
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        return Response({
            'store_id': 1,
            'store_name': 'Warung Makmur',
            'period': {
                'start': (timezone.now()-timedelta(days=30)).strftime('%Y-%m-%d'),
                'end': timezone.now().strftime('%Y-%m-%d'),
                'days': 30,
            },
            'sales_insights': {
                'total_sales': 15750000,
                'total_orders': 234,
                'avg_daily_sales': 525000,
                'avg_daily_orders': 7.8,
                'sales_growth_percent': 23.5,
                'order_growth_percent': 18.2,
                'avg_order_value': 67307,
                'best_day': {'date': '2026-06-15', 'total_sales': 1250000, 'order_count': 18},
                'summary': 'Total penjualan Rp 15.750.000 dari 234 pesanan. Naik 23.5% 📈',
            },
            'product_insights': {
                'top_products': [
                    {'product_name': 'Beras Premium 5kg', 'total_sold': 45, 'total_revenue': 2925000},
                    {'product_name': 'Minyak Goreng 1L', 'total_sold': 38, 'total_revenue': 684000},
                    {'product_name': 'Gula Pasir 1kg', 'total_sold': 32, 'total_revenue': 480000},
                ],
                'total_active_products': 48,
                'products_with_sales': 35,
                'summary': '35 dari 48 produk aktif memiliki penjualan.',
            },
            'customer_insights': {
                'total_customers': 87,
                'new_customers': 34,
                'returning_customers': 53,
                'return_rate': 60.9,
                'total_followers': 156,
                'new_followers': 22,
                'summary': '34 pelanggan baru, 53 pelanggan kembali (61% retensi).',
            },
            'inventory_insights': {
                'total_products': 48,
                'total_stock_units': 1250,
                'total_stock_value': 85000000,
                'healthy_stock': 33,
                'low_stock': 12,
                'out_of_stock': 3,
                'stock_health_percent': 68.8,
                'summary': '33 produk stok sehat, 12 stok rendah, 3 habis.',
            },
            'growth_insights': {
                'sales_growth_percent': 23.5,
                'order_growth_percent': 18.2,
                'growth_stage': 'growing',
                'growth_label': 'Berkembang',
                'summary': 'Berkembang: Penjualan naik 24% dibanding periode sebelumnya.',
            },
            'recommendations': [
                {
                    'type': 'inventory',
                    'priority': 'high',
                    'title': 'Stok Menipis',
                    'description': '12 produk memiliki stok rendah.',
                    'action': 'Restock sekarang',
                    'action_url': '/seller/products/',
                },
                {
                    'type': 'customer',
                    'priority': 'medium',
                    'title': 'Ulasan Belum Dibalas',
                    'description': '8 ulasan pelanggan belum mendapat balasan.',
                    'action': 'Lihat ulasan',
                    'action_url': '/seller/ulasan/',
                },
            ],
            'meta': {
                'api_version': '1.0.0',
                'source': 'mock',
            },
        })


class SellerReportView(views.APIView):
    """Live seller report built from existing order, product, review, and analytics records."""
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    COMPLETED_STATUSES = ['completed']

    def get(self, request):
        store = request.user.store
        start_date, end_date = self._date_range(request)
        days_count = max((end_date - start_date).days + 1, 1)
        prev_end = start_date - timedelta(days=1)
        prev_start = prev_end - timedelta(days=days_count - 1)

        current = self._period_metrics(store, start_date, end_date)
        previous = self._period_metrics(store, prev_start, prev_end)
        daily_sales = self._daily_sales(store, start_date, end_date)
        category_sales = self._category_sales(store, start_date, end_date)
        top_products = self._top_products(store, start_date, end_date)
        device_sales = self._device_breakdown(store, start_date, end_date)
        new_customer_days = self._new_customer_days(store, start_date, end_date)

        data = {
            'store': {
                'id': store.id,
                'store_name': store.store_name,
                'status': store.status,
            },
            'range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': days_count,
            },
            'metrics': current,
            'previous_metrics': previous,
            'trends': {
                'total_sales': self._pct_change(current['total_sales'], previous['total_sales']),
                'total_orders': self._pct_change(current['total_orders'], previous['total_orders']),
                'products_sold': self._pct_change(current['products_sold'], previous['products_sold']),
                'new_customers': self._pct_change(current['new_customers'], previous['new_customers']),
                'average_rating': round(current['average_rating'] - previous['average_rating'], 2),
            },
            'sales_chart': daily_sales,
            'category_sales': category_sales,
            'device_sales': device_sales,
            'top_products': top_products,
            'daily_sales': [
                {'date': row['date'], 'sales': row['sales'], 'orders': row['orders']}
                for row in daily_sales['rows']
            ],
            'performance': self._performance_summary(
                daily_sales['rows'], top_products, category_sales, device_sales, new_customer_days
            ),
        }
        return Response(data)

    def _date_range(self, request):
        today = timezone.localdate()
        period = request.query_params.get('period', '30days')
        if period == 'today':
            return today, today
        if period == '7days':
            return today - timedelta(days=6), today
        if period == 'this_month':
            return today.replace(day=1), today
        if period == 'this_year':
            return today.replace(month=1, day=1), today
        if period == 'custom':
            start_raw = request.query_params.get('start')
            end_raw = request.query_params.get('end')
            try:
                start = datetime.strptime(start_raw, '%Y-%m-%d').date()
                end = datetime.strptime(end_raw, '%Y-%m-%d').date()
                if start <= end:
                    return start, end
            except (TypeError, ValueError):
                pass
        return today - timedelta(days=29), today

    def _orders(self, store, start_date, end_date, completed_only=False):
        qs = Order.objects.filter(
            store=store,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
        )
        if completed_only:
            qs = qs.filter(order_status__in=self.COMPLETED_STATUSES)
        return qs

    def _period_metrics(self, store, start_date, end_date):
        completed = self._orders(store, start_date, end_date, completed_only=True)
        all_orders = self._orders(store, start_date, end_date)
        total_sales = completed.aggregate(total=Sum('total_price'))['total'] or Decimal('0')
        products_sold = OrderItem.objects.filter(order__in=completed).aggregate(total=Sum('qty'))['total'] or 0
        new_customers = self._new_customers_count(store, start_date, end_date)
        average_rating = Review.objects.filter(
            product__store=store,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
        ).aggregate(avg=Avg('rating'))['avg'] or 0
        return {
            'total_sales': float(total_sales),
            'total_orders': all_orders.count(),
            'products_sold': products_sold,
            'new_customers': new_customers,
            'average_rating': round(float(average_rating), 2),
        }

    def _new_customers_count(self, store, start_date, end_date):
        first_orders = Order.objects.filter(store=store, user__isnull=False).values('user').annotate(first=Min('created_at'))
        return sum(1 for row in first_orders if row['first'] and start_date <= row['first'].date() <= end_date)

    def _new_customer_days(self, store, start_date, end_date):
        first_orders = Order.objects.filter(store=store, user__isnull=False).values('user').annotate(first=Min('created_at'))
        counts = {}
        for row in first_orders:
            first = row['first']
            if first and start_date <= first.date() <= end_date:
                key = first.date().isoformat()
                counts[key] = counts.get(key, 0) + 1
        return counts

    def _daily_sales(self, store, start_date, end_date):
        rows = self._orders(store, start_date, end_date, completed_only=True).annotate(
            day=TruncDay('created_at')
        ).values('day').annotate(
            sales=Sum('total_price'),
            orders=Count('id'),
        ).order_by('day')
        indexed = {row['day'].date(): row for row in rows if row['day']}
        labels, sales, orders, table_rows = [], [], [], []
        current = start_date
        while current <= end_date:
            found = indexed.get(current)
            value = float(found['sales'] or 0) if found else 0
            count = found['orders'] if found else 0
            labels.append(current.strftime('%d %b'))
            sales.append(value)
            orders.append(count)
            table_rows.append({'date': current.isoformat(), 'label': current.strftime('%d %b %Y'), 'sales': value, 'orders': count})
            current += timedelta(days=1)
        return {'labels': labels, 'daily_sales': sales, 'daily_orders': orders, 'rows': table_rows}

    def _category_sales(self, store, start_date, end_date):
        rows = OrderItem.objects.filter(
            order__store=store,
            order__created_at__date__gte=start_date,
            order__created_at__date__lte=end_date,
            order__order_status__in=self.COMPLETED_STATUSES,
        ).values('product__category__category_name').annotate(
            revenue=Sum('subtotal'),
            quantity=Sum('qty'),
        ).order_by('-revenue')
        total = sum((row['revenue'] or Decimal('0')) for row in rows)
        return [{
            'category': row['product__category__category_name'] or 'Tanpa Kategori',
            'revenue': float(row['revenue'] or 0),
            'quantity': row['quantity'] or 0,
            'percentage': round(float((row['revenue'] or 0) / total * 100), 1) if total else 0,
        } for row in rows]

    def _top_products(self, store, start_date, end_date):
        rows = OrderItem.objects.filter(
            order__store=store,
            order__created_at__date__gte=start_date,
            order__created_at__date__lte=end_date,
            order__order_status__in=self.COMPLETED_STATUSES,
        ).values('product_id', 'product_name', 'product_photo').annotate(
            total_sold=Sum('qty'),
            total_revenue=Sum('subtotal'),
        ).order_by('-total_sold')[:5]
        return [{
            'product_id': row['product_id'],
            'product_name': row['product_name'] or 'Produk',
            'product_photo': row['product_photo'] or '',
            'total_sold': row['total_sold'] or 0,
            'total_revenue': float(row['total_revenue'] or 0),
        } for row in rows]

    def _device_breakdown(self, store, start_date, end_date):
        device_rows = DeviceAnalytics.objects.filter(
            store=store,
            date__gte=start_date,
            date__lte=end_date,
        ).values('device_type').annotate(count=Sum('visitors_count')).order_by('-count')

        if not device_rows:
            device_rows = UserActivity.objects.filter(
                store=store,
                created_at__date__gte=start_date,
                created_at__date__lte=end_date,
            ).exclude(device_type__isnull=True).exclude(device_type='').values('device_type').annotate(count=Count('id')).order_by('-count')

        total = sum(row['count'] or 0 for row in device_rows)
        return [{
            'device': row['device_type'],
            'count': row['count'] or 0,
            'percentage': round(((row['count'] or 0) / total) * 100, 1) if total else 0,
        } for row in device_rows]

    def _performance_summary(self, daily_rows, top_products, category_sales, device_sales, new_customer_days):
        best_day = max(daily_rows, key=lambda row: row['sales'], default=None)
        top_category = category_sales[0] if category_sales else None
        top_device = device_sales[0] if device_sales else None
        best_customer_day = max(new_customer_days.items(), key=lambda item: item[1], default=None)
        return {
            'best_day': {
                'label': best_day['label'] if best_day else '-',
                'value': best_day['sales'] if best_day else 0,
                'orders': best_day['orders'] if best_day else 0,
            },
            'top_product': top_products[0] if top_products else None,
            'top_category': top_category,
            'top_device': top_device,
            'new_customers_peak': {
                'date': best_customer_day[0] if best_customer_day else None,
                'count': best_customer_day[1] if best_customer_day else 0,
            },
        }

    def _pct_change(self, current, previous):
        current = float(current or 0)
        previous = float(previous or 0)
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return round(((current - previous) / previous) * 100, 1)
