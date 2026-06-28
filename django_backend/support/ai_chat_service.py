"""
AI Chat Service for Warungio Marketplace.
Provides intelligent responses to customer queries using Vertex AI.

Features:
- Automatic response generation
- Confidence scoring
- Escalation to human admin
- Chat history memory
- Context awareness
- FAQ support
"""

import json
import logging
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

import google.auth
from google.cloud import aiplatform
from google.api_core import gapic_v1

logger = logging.getLogger('django_backend')


class AIStreamingResponse:
    """Wrapper for streaming AI responses."""
    
    def __init__(self, stream_generator):
        self.stream = stream_generator
        self.full_response = ""
        
    def __iter__(self):
        """Iterate through streamed chunks."""
        try:
            for chunk in self.stream:
                if hasattr(chunk, 'candidates') and chunk.candidates:
                    for candidate in chunk.candidates:
                        if hasattr(candidate, 'content') and candidate.content:
                            for part in candidate.content.parts:
                                if hasattr(part, 'text'):
                                    text = part.text
                                    self.full_response += text
                                    yield text
        except Exception as e:
            logger.error(f"Error streaming AI response: {str(e)}")
            yield f"\n\n[Error: Unable to continue response - {str(e)}]"


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
        """Initialize Vertex AI client."""
        self.project_id = settings.GCP_PROJECT_ID
        self.region = getattr(settings, 'GCP_REGION', 'us-central1')
        self.endpoint_id = getattr(settings, 'VERTEX_AI_ENDPOINT_ID', 'openapi')
        self.model_name = getattr(
            settings, 
            'VERTEX_AI_MODEL', 
            'meta/llama-3.3-70b-instruct-maas'
        )
        
        # Initialize Vertex AI
        try:
            aiplatform.init(
                project=self.project_id,
                location=self.region
            )
            self.initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI: {str(e)}")
            self.initialized = False
    
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
        Calculate confidence score for AI response.
        
        Args:
            query: Customer query
            response: AI response
            
        Returns:
            Confidence score (0-1)
        """
        score = 0.8  # Default baseline
        
        # Check for uncertainty indicators
        uncertain_phrases = [
            'mungkin', 'kemungkinan', 'sepertinya', 'tidak yakin',
            'kurang tahu', 'i think', 'might', 'could be'
        ]
        
        response_lower = response.lower()
        if any(phrase in response_lower for phrase in uncertain_phrases):
            score -= 0.15
        
        # Check for complete answer indicators
        if len(response) > 50:  # Substantive response
            score += 0.1
        
        if '?' in response:  # Question for clarification
            score -= 0.1
        
        # Escalation keywords reduce confidence
        query_lower = query.lower()
        if any(kw in query_lower for kw in self.ESCALATION_KEYWORDS):
            score -= 0.1
        
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
        
        # Escalate if contains escalation keywords
        query_lower = query.lower()
        if any(kw in query_lower for kw in self.ESCALATION_KEYWORDS):
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
        Generate AI response to customer query.
        
        Args:
            query: Customer query
            customer_id: ID of the customer (optional)
            stream: Whether to stream response
            
        Returns:
            Tuple of (response, confidence_score, should_escalate)
        """
        if not self.initialized:
            logger.warning("Vertex AI not initialized, using fallback response")
            return self._get_fallback_response(query)
        
        try:
            # Build prompt
            system_prompt = self.build_system_prompt(customer_id)
            
            # Get chat context
            if customer_id:
                context = self.get_chat_context(customer_id)
                full_prompt = f"{system_prompt}\n\n{context}\n\nPelanggan: {query}"
            else:
                full_prompt = f"{system_prompt}\n\nPelanggan: {query}"
            
            # Call Vertex AI endpoint
            if stream:
                return self._generate_streaming_response(
                    full_prompt, customer_id
                )
            else:
                return self._generate_direct_response(
                    full_prompt, customer_id
                )
        
        except Exception as e:
            logger.error(f"Error generating AI response: {str(e)}")
            return self._get_fallback_response(query)
    
    def _generate_direct_response(
        self, 
        prompt: str, 
        customer_id: Optional[int] = None
    ) -> Tuple[str, float, bool]:
        """Generate direct (non-streaming) response."""
        try:
            client = aiplatform.gapic.PredictionServiceClient()
            
            endpoint_name = client.endpoint_path(
                project=self.project_id,
                location=self.region,
                endpoint=self.endpoint_id
            )
            
            request = {
                'endpoint': endpoint_name,
                'instances': [
                    {
                        'messages': [
                            {'role': 'user', 'content': prompt}
                        ]
                    }
                ],
                'parameters': {
                    'temperature': 0.7,
                    'max_output_tokens': 1024,
                    'top_p': 0.95,
                }
            }
            
            response = client.predict(request=request)
            
            # Parse response
            response_text = ""
            if response.predictions:
                pred = response.predictions[0]
                if isinstance(pred, dict) and 'content' in pred:
                    response_text = pred['content']
                elif hasattr(pred, 'get'):
                    response_text = pred.get('content', '')
            
            # Calculate confidence
            confidence = self.calculate_confidence_score(prompt, response_text)
            
            # Determine escalation
            should_escalate = self.should_escalate(prompt, response_text, confidence)
            
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
            logger.error(f"Error in direct response: {str(e)}")
            return self._get_fallback_response(prompt)
    
    def _generate_streaming_response(
        self, 
        prompt: str, 
        customer_id: Optional[int] = None
    ) -> Tuple[AIStreamingResponse, float, bool]:
        """Generate streaming response."""
        try:
            client = aiplatform.gapic.PredictionServiceClient()
            
            endpoint_name = client.endpoint_path(
                project=self.project_id,
                location=self.region,
                endpoint=self.endpoint_id
            )
            
            request = {
                'endpoint': endpoint_name,
                'instances': [
                    {
                        'messages': [
                            {'role': 'user', 'content': prompt}
                        ]
                    }
                ],
                'parameters': {
                    'temperature': 0.7,
                    'max_output_tokens': 1024,
                    'top_p': 0.95,
                    'stream': True,
                }
            }
            
            stream = client.predict(request=request)
            streaming_response = AIStreamingResponse(stream)
            
            # Confidence will be calculated after stream completes
            confidence = 0.7  # Default for streaming
            should_escalate = False
            
            return streaming_response, confidence, should_escalate
        
        except Exception as e:
            logger.error(f"Error in streaming response: {str(e)}")
            response_text, conf, esc = self._get_fallback_response(prompt)
            return response_text, conf, esc
    
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
    
    def _get_fallback_response(
        self, 
        query: str
    ) -> Tuple[str, float, bool]:
        """
        Get fallback response when AI is unavailable.
        
        Returns:
            Tuple of (response, confidence, should_escalate)
        """
        fallback_responses = {
            'refund': "Terima kasih telah menghubungi Warungio. Untuk pertanyaan tentang refund, silakan hubungi tim customer service kami yang siap membantu Anda 24/7. Confidence: 0.5",
            'order': "Untuk cek status pesanan Anda, silakan buka menu 'Pesanan Saya' di aplikasi. Confidence: 0.6",
            'product': "Kami menyediakan ribuan produk berkualitas dari warung-warung terpercaya. Ada yang bisa kami bantu? Confidence: 0.7",
            'default': "Terima kasih atas pertanyaannya. Tim kami sedang memproses, silakan hubungi admin jika perlu bantuan lebih lanjut. Confidence: 0.5"
        }
        
        query_lower = query.lower()
        
        # Match fallback responses
        for keyword, response in fallback_responses.items():
            if keyword != 'default' and keyword in query_lower:
                confidence = float(response.split(': ')[-1])
                should_escalate = confidence < self.MIN_CONFIDENCE_THRESHOLD
                return response.replace(f". Confidence: {confidence}", ""), confidence, should_escalate
        
        # Default response
        response = fallback_responses['default']
        confidence = float(response.split(': ')[-1])
        should_escalate = confidence < self.MIN_CONFIDENCE_THRESHOLD
        return response.replace(f". Confidence: {confidence}", ""), confidence, should_escalate


# Create singleton instance
_ai_service = None


def get_ai_chat_service() -> AIChatService:
    """Get or create AI chat service instance."""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIChatService()
    return _ai_service
