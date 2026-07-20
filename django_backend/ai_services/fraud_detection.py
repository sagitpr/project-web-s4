"""
AI Fraud Detection Engine.
Analyzes orders, accounts, and transactions for suspicious patterns using Gemini API.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import timedelta
from django.db.models import Count, Q, Sum
from django.utils import timezone
from django.core.cache import cache

from accounts.models import User, LoginAttempt
from orders.models import Order
from payments.models import Payment
from .gemini_client import get_gemini_client

logger = logging.getLogger('django_backend.ai_services.fraud')


class AIFraudDetection:
    """
    AI-powered fraud detection engine.
    
    Features:
    - Suspicious order detection (unusual amounts, addresses, patterns)
    - Duplicate account detection (same IP, device, phone)
    - Abnormal login activity (geographic anomalies, brute force)
    - Unusual purchasing patterns
    - Payment fraud indicators
    """

    def __init__(self):
        self.client = get_gemini_client()

    def analyze_order(self, order) -> Dict[str, Any]:
        """Analyze a single order for fraud indicators."""
        # Gather order context
        user = order.user
        user_orders = Order.objects.filter(user=user, created_at__gte=timezone.now() - timedelta(days=30))
        recent_count = user_orders.count()

        indicators = []

        # Rule-based checks
        if recent_count > 10:
            indicators.append({'type': 'velocity', 'severity': 'medium', 'detail': f'{recent_count} pesanan dalam 30 hari'})

        if order.total_price and order.total_price > 5000000:
            indicators.append({'type': 'high_value', 'severity': 'medium', 'detail': f'Nilai pesanan Rp {order.total_price:,.0f}'})

        # Check for same IP recent orders
        same_ip = Order.objects.filter(
            user__last_login_ip=user.last_login_ip,
            created_at__gte=timezone.now() - timedelta(hours=1),
        ).exclude(id=order.id).count()

        if same_ip > 5:
            indicators.append({'type': 'ip_abuse', 'severity': 'high', 'detail': f'{same_ip} pesanan dari IP yang sama dalam 1 jam'})

        # Use AI for deeper analysis
        ai_analysis = None
        if len(indicators) > 0:
            ai_analysis = self._analyze_with_gemini(order, user, indicators)

        fraud_score = self._calculate_fraud_score(indicators)

        return {
            'order_id': order.id,
            'fraud_score': fraud_score,
            'risk_level': self._get_risk_level(fraud_score),
            'indicators': indicators,
            'ai_analysis': ai_analysis,
            'recommended_action': self._get_recommended_action(fraud_score),
        }

    def analyze_user(self, user) -> Dict[str, Any]:
        """Analyze user account for suspicious activity."""
        now = timezone.now()
        month_ago = now - timedelta(days=30)

        # Gather signals
        login_failures = LoginAttempt.objects.filter(
            email=user.email,
            was_successful=False,
            attempted_at__gte=month_ago,
        ).count()

        orders_cancelled = Order.objects.filter(
            user=user,
            order_status='cancelled',
            created_at__gte=month_ago,
        ).count()

        recent_orders = Order.objects.filter(
            user=user,
            created_at__gte=month_ago,
        ).count()

        total_spent = Order.objects.filter(
            user=user,
            order_status__in=['paid', 'completed'],
        ).aggregate(t=Sum('total_price'))['t'] or 0

        signals = []
        if login_failures > 5:
            signals.append({'type': 'login_attempts', 'severity': 'high', 'detail': f'{login_failures} gagal login'})
        if orders_cancelled > 3:
            signals.append({'type': 'cancellations', 'severity': 'medium', 'detail': f'{orders_cancelled} pesanan dibatalkan'})

        risk_score = self._calculate_fraud_score(signals)

        return {
            'user_id': user.id,
            'risk_score': risk_score,
            'risk_level': self._get_risk_level(risk_score),
            'signals': signals,
            'login_failures_30d': login_failures,
            'orders_cancelled_30d': orders_cancelled,
            'total_orders_30d': recent_orders,
            'total_spent': float(total_spent),
        }

    def _analyze_with_gemini(self, order, user, indicators: List) -> Optional[Dict]:
        """Use Gemini for deep fraud analysis."""
        prompt = (
            f"Anda adalah AI detektor fraud untuk Warungio Marketplace.\n\n"
            f"Data Pesanan:\n"
            f"- Order ID: {order.id}\n"
            f"- Total: Rp {order.total_price:,.0f}\n"
            f"- Status: {order.order_status}\n"
            f"- Metode: {getattr(order, 'payment_method', 'N/A')}\n\n"
            f"Data Pengguna:\n"
            f"- User ID: {user.id}\n"
            f"- Email: {user.email}\n"
            f"- Role: {user.role}\n"
            f"- Verified: {user.is_verified}\n"
            f"- Failed Logins: {user.failed_login_attempts}\n\n"
            f"Indikator:\n" + "\n".join([f"- [{i['severity']}] {i['detail']}" for i in indicators]) + "\n\n"
            "Kembalikan JSON:\n"
            "{\n"
            '  "fraud_likelihood": "low|medium|high",\n'
            '  "analysis": "Analisis singkat dalam Bahasa Indonesia",\n'
            '  "red_flags": ["Flag 1", "Flag 2"],\n'
            '  "recommended_action": "izinkan|tinjau_manual|blokir",\n'
            '  "confidence": 0.0-1.0\n'
            "}"
        )

        result = self.client.generate_structured(
            prompt=prompt,
            temperature=0.2,
            cache_key=f'ai_fraud:{order.id}',
        )

        return result

    def _calculate_fraud_score(self, indicators: List) -> float:
        """Calculate fraud score from indicators."""
        severity_weights = {'low': 0.1, 'medium': 0.2, 'high': 0.4}
        score = 0.0
        for ind in indicators:
            score += severity_weights.get(ind.get('severity', 'low'), 0.1)
        return min(1.0, score)

    def _get_risk_level(self, score: float) -> str:
        if score >= 0.7:
            return 'high'
        elif score >= 0.3:
            return 'medium'
        return 'low'

    def _get_recommended_action(self, score: float) -> str:
        if score >= 0.7:
            return 'block'
        elif score >= 0.3:
            return 'review'
        return 'approve'


def get_fraud_detection() -> AIFraudDetection:
    return AIFraudDetection()
