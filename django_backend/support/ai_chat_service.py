"""
AI Chat Service for Warungio Marketplace.
Provides intelligent responses to customer queries using Gemini API.

Features:
- Automatic response generation via GeminiClient
- Confidence scoring based on real AI response analysis
- Escalation to human admin
- Chat history memory
- Context awareness
- FAQ support
"""

import json
import logging
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Union

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from ai_services.gemini_client import get_gemini_client

logger = logging.getLogger('django_backend')


class AIChatService:
    """
    AI Chat Service for customer support.
    
    Handles:
    - FAQ queries
    - Order status
    - Product recommendations
    - Refund policy
    - General support
    """
    
    # Confidence thresholds
    MIN_CONFIDENCE_THRESHOLD = 0.7  # 70% confidence
    HIGH_CONFIDENCE_THRESHOLD = 0.9  # 90% confidence
    
    # Escalation keywords
    ESCALATION_KEYWORDS = [
        'refund', 'complaint', 'issue', 'problem', 'tidak',
        'salah', 'rusak', 'error', 'gagal', 'fail'
    ]
    
    def __init__(self):
        """Initialize unified Gemini client."""
        self.client = get_gemini_client()
    
    def get_chat_context(self, customer_id: int, max_messages: int = 10) -> str:
        """
        Get chat history context for the customer.
        
        Args:
            customer_id: ID of the customer
            max_messages: Maximum number of recent messages to include
            
        Returns:
            Formatted chat context string
        """
        cache_key = f'chat_context:{customer_id}'
        context = cache.get(cache_key, [])
        
        if not context:
            # Fetch from database if not in cache
            from support.models import ChatMessage
            messages = ChatMessage.objects.filter(
                customer_id=customer_id
            ).order_by('-created_at')[:max_messages]
            
            context = []
            for msg in reversed(messages):
                context.append({
                    'role': msg.sender_type,  # 'customer', 'ai', or 'admin'
                    'content': msg.content,
                    'timestamp': msg.created_at.isoformat()
                })
            
            # Cache for 30 minutes
            cache.set(cache_key, context, 1800)
        
        # Format as string for prompt
        context_str = "Recent chat history:\n"
        for msg in context[-5:]:  # Show last 5 messages
            role = msg['role'].upper()
            context_str += f"{role}: {msg['content']}\n"
        
        return context_str
    
    def build_system_prompt(self, customer_id: Optional[int] = None) -> str:
        """
        Build system prompt with context and guidelines.
        
        Args:
            customer_id: ID of the customer (for personalization)
            
        Returns:
            System prompt string
        """
        prompt = """Anda adalah AI Customer Service Warungio, marketplace kebutuhan sehari-hari terpercaya.

Peran Anda:
1. Menjawab pertanyaan pelanggan dengan ramah dan profesional
2. Memberikan informasi akurat tentang produk, pesanan, dan kebijakan
3. Membantu menyelesaikan masalah pelanggan
4. Menggunakan bahasa Indonesia yang mudah dipahami

Kebijakan yang Penting:
- Garansi uang kembali 100% jika produk tidak sesuai
- Pengiriman gratis untuk pembelian > Rp50.000
- Jam layanan: 24/7
- Kami memiliki > 1000 warung terdaftar
- Produk segar dijamin kualitasnya

Panduan Respons:
- Jika pertanyaan tentang refund/komplain: Tawarkan solusi spesifik
- Jika tentang produk: Jelaskan fitur dan keuntungan
- Jika tentang pesanan: Berikan status tracking
- Jika tidak yakin: Tawarkan untuk dihubungkan ke admin

Hindari:
- Memberikan informasi yang tidak pasti
- Membuat janji yang tidak bisa dipenuhi
- Bahasa yang tidak sopan atau tidak profesional

Jika pelanggan menunjukkan kemarahan/frustasi, prioritaskan empati dan penyelesaian cepat."""
        
        return prompt
    
    def calculate_confidence_score(self, query: str, response: str) -> float:
        """
        Calculate confidence score for AI response using real content analysis.
        
        Args:
            query: Customer query
            response: AI response
            
        Returns:
            Confidence score (0-1)
        """
        if not response:
            return 0.0
        
        score = 0.8  # Default baseline
        
        # Check for uncertainty indicators in real response
        uncertain_phrases = [
            'mungkin', 'kemungkinan', 'sepertinya', 'tidak yakin',
            'kurang tahu', 'i think', 'might', 'could be', 'saya tidak tahu',
            'saya kurang', 'maaf saya tidak'
        ]
        
        response_lower = response.lower()
        if any(phrase in response_lower for phrase in uncertain_phrases):
            score -= 0.2
        
        # Check for complete answer indicators
        if len(response) > 80:  # Substantive response with detail
            score += 0.1
        
        if '?' in response:  # Question for clarification
            score -= 0.1
        
        # Escalation keywords reduce confidence
        query_lower = query.lower()
        if any(kw in query_lower for kw in self.ESCALATION_KEYWORDS):
            score -= 0.1
        
        # Check for actionable content (product names, order numbers, prices)
        if re.search(r'\d{4,}', response):  # Contains numbers (order IDs, prices)
            score += 0.05
        if 'Rp' in response:  # Contains pricing info
            score += 0.05
        
        return max(0, min(1, score))  # Clamp to 0-1
    
    def should_escalate(
        self, 
        query: str, 
        response: str, 
        confidence: float
    ) -> bool:
        """
        Determine if chat should be escalated to human admin.
        
        Args:
            query: Customer query
            response: AI response
            confidence: Confidence score
            
        Returns:
            True if should escalate to admin
        """
        # Escalate if low confidence
        if confidence < self.MIN_CONFIDENCE_THRESHOLD:
            return True
        
        # Escalate if no meaningful response
        if not response or len(response.strip()) < 20:
            return True
        
        # Escalate if contains escalation keywords
        query_lower = query.lower()
        if any(kw in query_lower for kw in self.ESCALATION_KEYWORDS):
            # Check if AI response handles the issue well
            handled_keywords = ['akan', 'sudah', 'diproses', 'dibantu', 'solusi']
            if not any(hk in response.lower() for hk in handled_keywords):
                return True
        
        # Escalate if asking for admin
        if any(phrase in query_lower for phrase in ['admin', 'manusia', 'orang', 'staff']):
            return True
        
        return False
    
    def generate_response(
        self, 
        query: str, 
        customer_id: Optional[int] = None,
        stream: bool = False
    ) -> Tuple[str, float, bool]:
        """
        Generate AI response to customer query using real Gemini API.
        
        Args:
            query: Customer query
            customer_id: ID of the customer (optional)
            stream: Whether to stream response (not yet supported)
            
        Returns:
            Tuple of (response, confidence_score, should_escalate)
            
        Raises:
            Returns fallback escalation tuple if AI is unavailable
        """
        if not self.client.api_key:
            logger.warning("Gemini API key not configured, returning escalation prompt")
            return (
                "Maaf, layanan AI sedang tidak tersedia. Silakan hubungi admin untuk bantuan lebih lanjut.",
                0.3,
                True
            )
        
        try:
            # Build prompt
            system_prompt = self.build_system_prompt(customer_id)
            
            # Get chat context
            if customer_id:
                context = self.get_chat_context(customer_id)
                full_prompt = f"{system_prompt}\n\n{context}\n\nPelanggan: {query}"
            else:
                full_prompt = f"{system_prompt}\n\nPelanggan: {query}"
            
            # Call Gemini API via unified client
            response_text = self.client.generate_text(
                prompt=full_prompt,
                temperature=0.7,
                max_output_tokens=1024,
            )
            
            if not response_text:
                logger.warning("Gemini returned empty response for chat query")
                return (
                    "Maaf, saya tidak dapat memproses pertanyaan Anda saat ini. "
                    "Silakan coba lagi atau hubungi admin.",
                    0.3,
                    True
                )
            
            # Calculate confidence
            confidence = self.calculate_confidence_score(query, response_text)
            
            # Determine escalation
            should_escalate = self.should_escalate(query, response_text, confidence)
            
            # Store in chat history
            if customer_id and response_text:
                self._save_chat_message(
                    customer_id, 
                    response_text, 
                    'ai'
                )
                # Invalidate cache
                cache.delete(f'chat_context:{customer_id}')
            
            return response_text, confidence, should_escalate
        
        except Exception as e:
            logger.error(f"Error generating AI response: {str(e)}")
            return (
                "Maaf, terjadi kesalahan teknis. Silakan coba lagi atau hubungi admin.",
                0.2,
                True
            )
    
    def _save_chat_message(
        self, 
        customer_id: int, 
        content: str, 
        sender_type: str
    ):
        """Save chat message to database."""
        try:
            from support.models import ChatMessage
            
            ChatMessage.objects.create(
                customer_id=customer_id,
                content=content,
                sender_type=sender_type,
                is_ai_response=sender_type == 'ai'
            )
        except Exception as e:
            logger.error(f"Error saving chat message: {str(e)}")


# Create singleton instance
_ai_service = None


def get_ai_chat_service() -> AIChatService:
    """Get or create AI chat service instance."""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIChatService()
    return _ai_service
