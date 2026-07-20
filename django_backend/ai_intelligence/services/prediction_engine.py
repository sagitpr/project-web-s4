"""
AI Prediction Engine.
Demand forecasting, pricing recommendations, and sales predictions.
"""

import logging
from datetime import timedelta, date
from decimal import Decimal
from typing import Dict, Optional
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone

logger = logging.getLogger(__name__)


class PredictionEngine:
    """
    AI-powered prediction engine.
    Generates demand forecasts, pricing recommendations, and sales predictions.
    """

    def predict_demand(self, product, days_ahead: int = 7) -> Dict:
        """Predict demand for a product."""
        from orders.models import OrderItem
        from ai_intelligence.models import DemandPrediction

        now = timezone.now()
        store = product.store

        # Historical sales (query through order's created_at)
        history_7d = OrderItem.objects.filter(
            product=product, order__created_at__gte=now - timedelta(days=7)
        ).aggregate(total=Sum('qty'))['total'] or 0

        history_30d = OrderItem.objects.filter(
            product=product, order__created_at__gte=now - timedelta(days=30)
        ).aggregate(total=Sum('qty'))['total'] or 0

        # Daily average
        daily_avg_7d = history_7d / 7.0
        daily_avg_30d = history_30d / 30.0

        # Weighted average (recent data weighted more)
        weighted_avg = (daily_avg_7d * 0.7) + (daily_avg_30d * 0.3)

        # Predicted demand
        predicted = max(0, int(weighted_avg * days_ahead))
        low = max(0, int(predicted * 0.7))
        high = int(predicted * 1.3)

        # Confidence (higher with more data)
        confidence = min(0.9, 0.3 + (history_30d / 100))

        # Days until stockout
        days_until_stockout = int(product.stock / max(weighted_avg, 0.1))

        return {
            'predicted_demand': predicted,
            'predicted_demand_low': low,
            'predicted_demand_high': high,
            'confidence_score': round(confidence, 4),
            'recommended_stock': max(0, int(weighted_avg * days_ahead * 1.5)),
            'restock_urgency': 'critical' if days_until_stockout <= 3 else (
                'high' if days_until_stockout <= 7 else (
                    'normal' if days_until_stockout <= 14 else 'low'
                )
            ),
            'days_until_stockout': days_until_stockout,
            'predicted_revenue': predicted * float(product.price),
        }

    def recommend_price(self, product) -> Dict:
        """Recommend optimal pricing for a product."""
        from ai_intelligence.models import PricingRecommendation
        from orders.models import OrderItem

        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)

        current_price = float(product.price)

        # Historical sales at current price (via order's created_at)
        sales_30d = OrderItem.objects.filter(
            product=product, order__created_at__gte=thirty_days_ago
        ).aggregate(total=Sum('qty'), revenue=Sum('subtotal'))['total'] or 0

        # Price elasticity estimation
        if sales_30d == 0:
            elasticity = -0.5  # Default
        else:
            elasticity = -0.5  # Simplified

        # Price ranges
        min_price = current_price * 0.8
        max_price = current_price * 1.2

        # Simple recommendation
        if sales_30d > 20:
            # High demand — can increase price
            recommended = current_price * 1.05
            strategy = 'premium'
        elif sales_30d > 5:
            # Moderate demand — maintain
            recommended = current_price
            strategy = 'competitive'
        else:
            # Low demand — reduce price
            recommended = current_price * 0.9
            strategy = 'penetration'

        expected_demand_change = ((recommended - current_price) / current_price) * elasticity * 100
        expected_revenue_change = expected_demand_change + ((recommended - current_price) / current_price) * 100

        return {
            'current_price': current_price,
            'recommended_price': round(recommended, 2),
            'min_price': round(min_price, 2),
            'max_price': round(max_price, 2),
            'price_change_pct': round(((recommended - current_price) / current_price) * 100, 1),
            'expected_demand_change': round(expected_demand_change, 1),
            'expected_revenue_change': round(expected_revenue_change, 1),
            'confidence_score': round(min(0.8, 0.3 + sales_30d / 50), 4),
            'strategy': strategy,
            'reasoning': self._get_pricing_reasoning(strategy, sales_30d, current_price, recommended),
        }

    def _get_pricing_reasoning(self, strategy: str, sales: int,
                                current: float, recommended: float) -> str:
        """Generate AI-style reasoning for pricing recommendation."""
        if strategy == 'premium':
            return f'Produk ini laris ({sales} terjual). Naikkan harga Rp {recommended - current:,.0f} untuk margin lebih tinggi.'
        elif strategy == 'penetration':
            return f'Penjualan rendah ({sales}). Turunkan harga Rp {current - recommended:,.0f} untuk menarik pembeli.'
        return f'Harga kompetitif. Pertahankan harga saat ini Rp {current:,.0f}.'

    def forecast_sales(self, store, period: str = 'weekly', weeks: int = 4) -> Dict:
        """Forecast sales for a store."""
        from orders.models import Order
        from ai_intelligence.models import SalesForecast

        now = timezone.now()
        results = []

        for week in range(weeks):
            forecast_date = (now + timedelta(weeks=week)).date()

            # Historical same-day-of-week average
            same_dow = Order.objects.filter(
                store=store,
                created_at__week_day=forecast_date.isoweekday() + 1
            ).aggregate(
                total=Sum('total_price'),
                count=Count('id')
            )

            historical_avg = float(same_dow['total'] or 0) / max(same_dow['count'] or 1, 1)
            forecast = historical_avg * 1.05  # 5% growth factor

            results.append({
                'forecast_date': forecast_date,
                'predicted_revenue': round(forecast, 2),
                'predicted_orders': max(1, int(same_dow['count'] or 0)),
            })

        return {
            'store_id': store.id,
            'period': period,
            'weeks': weeks,
            'forecasts': results,
            'total_predicted_revenue': sum(r['predicted_revenue'] for r in results),
        }

    def predict_customer_lifetime_value(self, user) -> Decimal:
        """Predict customer lifetime value."""
        from ai_intelligence.services.digital_twin import get_digital_twin_engine
        from engagement.models import UserBehaviorProfile
        twin_engine = get_digital_twin_engine()
        profile, _ = UserBehaviorProfile.objects.get_or_create(user=user)
        return twin_engine._compute_clv(user, profile)


# Singleton
_prediction_engine = None


def get_prediction_engine() -> PredictionEngine:
    global _prediction_engine
    if _prediction_engine is None:
        _prediction_engine = PredictionEngine()
    return _prediction_engine
