"""
AI Chat Service for Warungio Marketplace.

Provides AI-powered customer service responses using Gemini API.
Uses the unified GeminiClient from ai_services for all inference.
"""

import json
import logging
from typing import Optional, Tuple

from django.conf import settings

from ai_services.gemini_client import get_gemini_client

logger = logging.getLogger(__name__)


class AIChatService:
    """
    AI-powered customer service chat service using Gemini API.
    Generates real AI responses based on customer queries and context.
    """

    # Escalation indicators
    ESCALATION_PHRASES = [
        'admin', 'manusia', 'staff', 'komplain', 'rusak', 'salah',
        'tidak puas', 'gagal', 'error', 'refund',
    ]

    def __init__(self):
        self.client = get_gemini_client()
        self.is_available = bool(self.client.api_key)
        if self.is_available:
            logger.info("AIChatService initialized with Gemini API")
        else:
            logger.warning("AIChatService initialized without API key")

    def generate_response(
        self,
        query: str,
        customer_id: Optional[int] = None,
        stream: bool = False,
    ) -> Tuple[str, float, bool]:
        """
        Generate AI response to customer query using Gemini.

        Args:
            query: The customer's message.
            customer_id: Optional authenticated user ID.
            stream: Whether to stream response tokens.

        Returns:
            Tuple of (response_text, confidence, should_escalate)
        """
        if not self.is_available:
            logger.warning("Gemini not available, returning fallback")
            return self._fallback_response(query)

        # Build store context
        store_context = ""
        if customer_id:
            try:
                from accounts.models import User
                user = User.objects.filter(id=customer_id).first()
                if user:
                    store_context = (
                        f"Pelanggan: {user.full_name or user.email}\n"
                        f"Role: {user.role}\n"
                    )
                    # Get recent orders context
                    from orders.models import Order
                    recent_orders = Order.objects.filter(
                        user=user
                    ).order_by('-created_at')[:3]
                    if recent_orders:
                        store_context += "Pesanan Terbaru:\n"
                        for o in recent_orders:
                            store_context += f"- Order #{o.id}: {o.order_status}, Rp {o.total_price:,.0f}\n"
            except Exception:
                pass

        system_prompt = (
            "Anda adalah AI Customer Service Warungio, marketplace kebutuhan sehari-hari Indonesia.\n\n"
            "Tugas Anda:\n"
            "1. Jawab pertanyaan pelanggan dengan ramah dan profesional dalam Bahasa Indonesia\n"
            "2. Berikan informasi akurat tentang produk, pesanan, pengiriman, dan pembayaran\n"
            "3. Bantu selesaikan masalah pelanggan dengan solusi praktis\n"
            "4. Rekomendasikan produk sesuai kebutuhan pelanggan\n"
            "5. Jelaskan promo dan diskon yang tersedia\n\n"
            "Informasi Warungio:\n"
            "- Marketplace hyperlocal untuk kebutuhan harian dan produk segar\n"
            "- Pembayaran: Midtrans (Kartu Kredit, Bank Transfer, QRIS, GoPay, OVO, DANA, ShopeePay), COD\n"
            "- Pengiriman: GoSend, GrabExpress, Maxim, Antar Sendiri\n"
            "- Jam layanan: 24/7\n"
            "- Garansi uang kembali jika produk tidak sesuai\n\n"
            "Jika pelanggan meminta admin/manusia atau memiliki masalah kompleks, "
            "tawarkan untuk dihubungkan ke tim support. "
            "Jangan pernah memberikan informasi yang tidak pasti atau membuat janji palsu."
        )

        full_prompt = f"{store_context}Pelanggan: {query}\n\nRespon dengan ramah dan membantu:"

        try:
            response = self.client.generate_text(
                prompt=full_prompt,
                system_instruction=system_prompt,
                temperature=0.7,
                max_output_tokens=1024,
            )

            if response:
                confidence = self._calculate_confidence(query, response)
                should_escalate = self._should_escalate(query, response, confidence)
                return response, confidence, should_escalate

        except Exception as e:
            logger.error("AI chat generation error: %s", e)

        return self._fallback_response(query)

    def _calculate_confidence(self, query: str, response: str) -> float:
        """Calculate confidence score based on response quality."""
        score = 0.8
        if len(response) < 20:
            score -= 0.3
        if any(p in response.lower() for p in ['mungkin', 'tidak yakin', 'maaf']):
            score -= 0.15
        if '?' in query and '?' in response:
            score -= 0.1
        return max(0, min(1, score))

    def _should_escalate(self, query: str, response: str, confidence: float) -> bool:
        """Determine if the conversation should escalate to a human."""
        if confidence < 0.4:
            return True
        query_lower = query.lower()
        if any(p in query_lower for p in self.ESCALATION_PHRASES):
            return True
        return False

    def _fallback_response(self, query: str) -> Tuple[str, float, bool]:
        """Return a minimal fallback when AI is unavailable."""
        return (
            "Maaf, layanan AI sedang tidak tersedia. Silakan hubungi tim support kami "
            "melalui WhatsApp atau email untuk bantuan lebih lanjut. Terima kasih.",
            0.0,
            True,
        )


_service_instance = None


def get_ai_chat_service():
    """
    Return the singleton AI chat service instance.
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = AIChatService()
    return _service_instance
