"""
AI Chat Service for Warungio Marketplace.

Provides AI-powered customer service responses.
Currently configured as a graceful fallback that returns a friendly
default message when the AI service is not yet connected.
"""

import logging
import random

logger = logging.getLogger(__name__)


class AIChatService:
    """
    AI-powered customer service chat service.

    When the AI model/API is unavailable, falls back to a curated list of
        context-aware responses to keep the conversation helpful.
    """

    def __init__(self):
        self.is_available = False
        logger.info("AIChatService initialized (fallback mode: AI model not configured)")

    def generate_response(self, query: str, customer_id=None, stream=False):
        """
        Generate a response to the customer query.

        Args:
            query: The customer's message.
            customer_id: Optional authenticated user ID.
            stream: Whether to stream the response token by token.

        Returns:
            Tuple of (response_text, confidence, should_escalate)
        """
        confidence = 0.0
        query_lower = query.strip().lower()

        # Simple keyword matching for basic Q&A
        if any(kw in query_lower for kw in ['pesanan', 'order', 'tracking', 'dimana']):
            response = (
                "Untuk mengecek status pesanan, silakan buka halaman "
                "'Pesanan Saya' di dashboard atau gunakan fitur tracking "
                "pengiriman. Jika butuh bantuan lebih lanjut, tim support "
                "kami siap membantu."
            )
            confidence = 0.3
        elif any(kw in query_lower for kw in ['pembayaran', 'bayar', 'payment', 'transaksi']):
            response = (
                "Warungio menerima pembayaran melalui Midtrans (Kartu Kredit, "
                "Bank Transfer, QRIS, GoPay, OVO, DANA, ShopeePay) dan "
                "Cash on Delivery (COD) untuk area tertentu."
            )
            confidence = 0.3
        elif any(kw in query_lower for kw in ['refund', 'kembali', 'pengembalian', 'komplain']):
            response = (
                "Untuk pengajuan refund/pengembalian, silakan buka halaman "
                "'Refund Saya' di dashboard dan ajukan permohonan refund "
                "untuk pesanan yang sesuai. Tim kami akan memproses dalam "
                "1x24 jam."
            )
            confidence = 0.3
        elif any(kw in query_lower for kw in ['akun', 'login', 'daftar', 'register', 'password']):
            response = (
                "Untuk masalah akun, seperti login, registrasi, atau reset "
                "password, silakan gunakan fitur 'Lupa Password' di halaman "
                "login atau hubungi support kami via WhatsApp."
            )
            confidence = 0.3
        elif any(kw in query_lower for kw in ['halo', 'hi', 'hai', 'siang', 'pagi', 'malam', 'helo']):
            response = (
                "Halo! Selamat datang di Warungio. Ada yang bisa kami bantu? "
                "Kami siap membantu pertanyaan seputar pesanan, pembayaran, "
                "pengiriman, atau akun Anda."
            )
            confidence = 0.4
        else:
            response = (
                "Terima kasih telah menghubungi Warungio. Untuk pertanyaan "
                "lebih lanjut, silakan hubungi tim support kami melalui "
                "WhatsApp atau email. Kami siap membantu Anda!"
            )
            confidence = 0.1

        should_escalate = confidence < 0.2

        logger.info(
            "AI chat: query='%s', confidence=%.2f, escalate=%s",
            query[:60], confidence, should_escalate,
        )

        return response, confidence, should_escalate


_service_instance = None


def get_ai_chat_service():
    """
    Return the singleton AI chat service instance.
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = AIChatService()
    return _service_instance
