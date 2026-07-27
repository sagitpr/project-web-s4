"""
Smart Stock Prediction Service for Warungio Marketplace.
AI-powered stock forecasting, reorder recommendations, and demand prediction.

This service uses statistical time-series analysis (moving averages, trend analysis)
to predict future stock needs based on historical sales data.
"""

import math
from datetime import timedelta, date
from decimal import Decimal
from collections import defaultdict

from django.db.models import Sum, Avg, Count, F, Q
from django.utils import timezone

from orders.models import Order, OrderItem
from products.models import Product


class StockPredictor:
    """
    Stock demand forecasting engine.
    Predicts future stock requirements using historical sales data.
    """

    def __init__(self, product=None, store=None):
        self.product = product
        self.store = store

    def get_daily_sales_history(self, product, days=90):
        """Get daily sales quantity for a product over the specified period."""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        sales_data = OrderItem.objects.filter(
            product=product,
            order__created_at__date__gte=start_date,
            order__created_at__date__lte=end_date,
            order__order_status__in=['paid', 'completed', 'shipped', 'processed'],
        ).values('order__created_at__date').annotate(
            qty_sold=Sum('qty'),
            revenue=Sum('subtotal'),
        ).order_by('order__created_at__date')

        # Build daily map
        daily = {}
        for entry in sales_data:
            d = entry['order__created_at__date']
            daily[d.isoformat()] = {
                'qty': entry['qty_sold'],
                'revenue': float(entry['revenue'] or 0),
            }

        # Fill in zero-sale days
        result = []
        current = start_date
        while current <= end_date:
            key = current.isoformat()
            if key in daily:
                result.append({'date': key, 'qty': daily[key]['qty'], 'revenue': daily[key]['revenue']})
            else:
                result.append({'date': key, 'qty': 0, 'revenue': 0})
            current += timedelta(days=1)

        return result

    def moving_average(self, data, window=7):
        """Calculate simple moving average."""
        if len(data) < window:
            return data
        result = []
        for i in range(len(data)):
            if i < window - 1:
                result.append(None)
            else:
                window_data = data[i - window + 1:i + 1]
                avg = sum(d['qty'] for d in window_data) / window
                result.append(round(avg, 1))
        return result

    def exponential_smoothing(self, data, alpha=0.3):
        """Calculate exponential smoothing forecast."""
        if not data:
            return []
        result = [data[0]['qty']]  # First value
        for i in range(1, len(data)):
            forecast = alpha * data[i - 1]['qty'] + (1 - alpha) * result[-1]
            result.append(round(forecast, 1))
        return result

    def predict_demand(self, product=None, days_ahead=30, history_days=90):
        """
        Predict demand for a product over the specified future period.
        
        Returns:
            dict with predicted_demand, confidence_score, recommended_reorder_qty, 
            reorder_point, safety_stock, days_until_stockout
        """
        p = product or self.product
        if not p:
            return {'error': 'Product is required.'}

        sales_history = self.get_daily_sales_history(p, history_days)
        recent_sales = [s['qty'] for s in sales_history]

        if not recent_sales or sum(recent_sales) == 0:
            return {
                'product_id': p.id,
                'product_name': p.product_name,
                'status': 'insufficient_data',
                'message': 'Belum ada data penjualan untuk prediksi.',
                'predicted_daily_demand': 0,
                'predicted_monthly_demand': 0,
                'confidence_score': 0,
                'recommended_reorder_qty': 0,
            }

        # Calculate metrics
        total_sold = sum(recent_sales)
        avg_daily = total_sold / len(recent_sales) if recent_sales else 0

        # Trend analysis (linear regression simplified)
        if len(recent_sales) >= 14:
            # Split into two halves to detect trend
            half = len(recent_sales) // 2
            first_half_avg = sum(recent_sales[:half]) / half
            second_half_avg = sum(recent_sales[half:]) / (len(recent_sales) - half)
            trend_factor = (second_half_avg - first_half_avg) / first_half_avg if first_half_avg > 0 else 0
        else:
            trend_factor = 0

        # Seasonality detection (weekly pattern)
        if len(recent_sales) >= 14:
            weekly_pattern = defaultdict(list)
            for i, s in enumerate(sales_history):
                day_of_week = timezone.datetime.fromisoformat(s['date']).weekday()
                weekly_pattern[day_of_week].append(s['qty'])
            day_multipliers = {}
            for day, qtys in weekly_pattern.items():
                day_avg = sum(qtys) / len(qtys) if qtys else 0
                day_multipliers[day] = day_avg / avg_daily if avg_daily > 0 else 1.0
        else:
            day_multipliers = {i: 1.0 for i in range(7)}

        # Predict future demand
        predicted_daily = []
        current_stock = p.stock
        for day_offset in range(days_ahead):
            future_date = timezone.now().date() + timedelta(days=day_offset)
            day_of_week = future_date.weekday()
            multiplier = day_multipliers.get(day_of_week, 1.0)
            day_demand = avg_daily * multiplier * (1 + trend_factor)
            predicted_daily.append({
                'date': future_date.isoformat(),
                'predicted_demand': round(day_demand, 1),
            })

        total_predicted = sum(d['predicted_demand'] for d in predicted_daily)
        avg_predicted_daily = total_predicted / days_ahead if days_ahead > 0 else 0

        # Safety stock calculation (using standard deviation)
        if len(recent_sales) >= 7:
            mean = sum(recent_sales[-30:]) / min(30, len(recent_sales)) if len(recent_sales) >= 30 else avg_daily
            variance = sum((x - mean) ** 2 for x in recent_sales[-30:]) / min(30, len(recent_sales))
            std_dev = math.sqrt(variance)
            safety_stock = round(std_dev * 1.65)  # 95% service level (Z=1.65)
        else:
            safety_stock = round(avg_daily * 3)  # Default: 3 days buffer

        reorder_point = round(avg_predicted_daily * (p.unit if p.unit is not None else 7)) + safety_stock

        # Days until stockout
        if avg_predicted_daily > 0 and current_stock > 0:
            days_until_stockout = round(current_stock / avg_predicted_daily, 1)
        else:
            days_until_stockout = 0 if current_stock <= 0 else 30

        # Recommended reorder quantity
        lead_time_days = 3  # Default lead time
        reorder_qty = round(total_predicted) + safety_stock - current_stock
        reorder_qty = max(reorder_qty, 0)

        # Confidence score (based on data volume and variance)
        if len(recent_sales) >= 90:
            confidence = 0.90
        elif len(recent_sales) >= 30:
            confidence = 0.75
        elif len(recent_sales) >= 14:
            confidence = 0.55
        else:
            confidence = 0.30

        # Coefficient of variation penalty
        if avg_daily > 0:
            cv = math.sqrt(variance) / avg_daily if len(recent_sales) >= 7 else 1.0
            confidence *= max(0, 1 - cv * 0.3)

        return {
            'product_id': p.id,
            'product_name': p.product_name,
            'current_stock': current_stock,
            'unit': p.unit or 'pcs',
            'status': 'sufficient_data',
            'predicted_daily_demand': round(avg_predicted_daily, 1),
            'predicted_monthly_demand': round(total_predicted, 1),
            'predicted_daily_breakdown': predicted_daily[:30],  # First 30 days
            'confidence_score': round(confidence, 2),
            'safety_stock': safety_stock,
            'reorder_point': reorder_point,
            'recommended_reorder_qty': reorder_qty,
            'days_until_stockout': days_until_stockout,
            'trend_direction': 'up' if trend_factor > 0.05 else ('down' if trend_factor < -0.05 else 'stable'),
            'trend_factor': round(trend_factor, 3),
            'avg_daily_sales': round(avg_daily, 1),
            'lead_time_days': lead_time_days,
            'total_sold_last_90d': total_sold,
            'forecast_period_days': days_ahead,
            'analysis_date': timezone.now().isoformat(),
        }

    def predict_store_stock(self, store, days_ahead=30):
        """
        Predict stock needs for all products in a store.
        
        Returns:
            list of predictions per product
        """
        products = Product.objects.filter(
            store=store, is_active=True
        ).select_related('category')

        predictions = []
        for product in products:
            prediction = self.predict_demand(product, days_ahead)
            predictions.append(prediction)

        # Sort by urgency (days until stockout ascending)
        predictions.sort(key=lambda x: (
            0 if x.get('days_until_stockout', 999) == 0
            else x.get('days_until_stockout', 999)
        ))

        return {
            'store_id': store.id,
            'store_name': store.store_name,
            'total_products': len(products),
            'low_stock_count': sum(1 for p in predictions if p.get('days_until_stockout', 999) <= 7),
            'out_of_stock_count': sum(1 for p in predictions if p.get('current_stock', 0) <= 0),
            'predictions': predictions[:50],  # Top 50 urgent
            'generated_at': timezone.now().isoformat(),
        }


class ReorderOptimizer:
    """
    Optimize reorder quantities and timing.
    Suggests optimal order quantities based on demand, lead time, and costs.
    """

    def __init__(self, store):
        self.store = store

    def calculate_economic_order_quantity(self, annual_demand, ordering_cost=50000,
                                           holding_cost_percent=0.2, unit_cost=10000):
        """
        Calculate Economic Order Quantity (EOQ).
        EOQ = sqrt(2 * D * S / H)
        where D = annual demand, S = ordering cost, H = holding cost per unit
        """
        if annual_demand <= 0:
            return 0
        holding_cost = unit_cost * holding_cost_percent
        if holding_cost <= 0:
            return annual_demand
        eoq = math.sqrt(2 * annual_demand * ordering_cost / holding_cost)
        return round(eoq)

    def get_reorder_suggestions(self):
        """
        Get comprehensive reorder suggestions for all products.
        """
        predictor = StockPredictor(store=self.store)
        predictions = predictor.predict_store_stock(self.store)
        suggestions = []

        for pred in predictions.get('predictions', []):
            if pred.get('status') == 'insufficient_data':
                continue

            annual_demand = pred.get('predicted_monthly_demand', 0) * 12
            eoq = self.calculate_economic_order_quantity(
                annual_demand=annual_demand,
                unit_cost=pred.get('avg_price', 10000),
            )

            suggestions.append({
                **pred,
                'economic_order_qty': eoq,
                'order_urgency': self._get_urgency(pred),
                'suggested_action': self._get_action(pred),
            })

        return {
            'store_id': self.store.id,
            'total_suggestions': len(suggestions),
            'urgent_reorders': [s for s in suggestions if s.get('order_urgency') == 'urgent'],
            'suggestions': suggestions,
        }

    def _get_urgency(self, prediction):
        days = prediction.get('days_until_stockout', 999)
        if days <= 0:
            return 'critical'
        elif days <= 3:
            return 'urgent'
        elif days <= 7:
            return 'high'
        elif days <= 14:
            return 'medium'
        else:
            return 'low'

    def _get_action(self, prediction):
        days = prediction.get('days_until_stockout', 999)
        reorder_qty = prediction.get('recommended_reorder_qty', 0)

        if days <= 0:
            return f'STOK HABIS! Segera pesan {reorder_qty} {prediction.get("unit", "pcs")}'
        elif days <= 3:
            return f'Kritis! Pesan {reorder_qty} {prediction.get("unit", "pcs")} segera'
        elif days <= 7:
            return f'Pesan {reorder_qty} {prediction.get("unit", "pcs")} minggu ini'
        elif days <= 14:
            return f'Rencanakan pemesanan {reorder_qty} {prediction.get("unit", "pcs")}'
        else:
            return f'Stok aman. Reorder {reorder_qty} {prediction.get("unit", "pcs")} jika diperlukan'
