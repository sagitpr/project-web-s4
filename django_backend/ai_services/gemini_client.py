"""
Gemini API Client — Unified interface for all Google Gemini API calls.
Supports text generation, vision (image analysis), and structured JSON output.
Uses GEMINI_KEY or VERTEX_KEY from environment as the API key.
"""

import json
import logging
import base64
import os
import time
from typing import Optional, Dict, Any, List
from django.conf import settings
from django.core.cache import cache
import requests

logger = logging.getLogger('django_backend.ai_services')


class GeminiClient:
    """
    Unified Gemini API client for all Warungio AI features.
    
    - Text generation (chat, descriptions, reviews, insights)
    - Vision analysis (product images, freshness, OCR)
    - Structured JSON output with configurable temperature
    - Automatic retry with exponential backoff
    - Response caching for repeated queries
    """

    MODEL_TEXT = "gemini-2.0-flash"
    MODEL_VISION = "gemini-2.0-flash"
    MODEL_PRO = "gemini-2.0-pro"

    def __init__(self):
        # Use settings.GEMINI_KEY with fallback to direct env var (legacy, case variations)
        self.api_key = getattr(settings, 'GEMINI_KEY', '') \
            or os.environ.get('GEMINI_KEY', '') \
            or os.environ.get('Gemini_key', '') \
            or os.environ.get('VERTEX_KEY', '') \
            or os.environ.get('Vertex_key', '') \
            or os.environ.get('GOOGLE_API_KEY', '')
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.cache_ttl = getattr(settings, 'AI_CACHE_TTL', 3600)  # 1 hour default
        self.max_retries = 2
        self.timeout = 30

        if not self.api_key:
            logger.warning("No Gemini API key found. Set GEMINI_KEY or VERTEX_KEY in .env")

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
        }

    def _build_url(self, model: str, action: str = "generateContent") -> str:
        """Build the Gemini API URL for a given model and action."""
        key = self.api_key
        return f"{self.base_url}/models/{model}:{action}?key={key}"

    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model: str = None,
        temperature: float = 0.7,
        max_output_tokens: int = 1024,
        response_mime_type: Optional[str] = None,
        cache_key: Optional[str] = None,
    ) -> Optional[str]:
        """
        Generate text using Gemini API.
        
        Args:
            prompt: User prompt
            system_instruction: Optional system-level instruction
            model: Model name (default: gemini-2.0-flash)
            temperature: 0.0-1.0 (lower = more deterministic)
            max_output_tokens: Maximum response length
            response_mime_type: Set to "application/json" for JSON output
            cache_key: Optional cache key to cache response
            
        Returns:
            Generated text string, or None on failure
        """
        # Check cache first
        if cache_key:
            cached = cache.get(cache_key)
            if cached:
                logger.debug("AI cache hit: %s", cache_key)
                return cached

        model = model or self.MODEL_TEXT
        url = self._build_url(model)

        contents = [{"parts": [{"text": prompt}]}]
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_output_tokens,
                "topP": 0.95,
                "topK": 40,
            }
        }

        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        if response_mime_type:
            payload["generationConfig"]["responseMimeType"] = response_mime_type

        result = self._call_api(url, payload)
        if result and cache_key:
            cache.set(cache_key, result, self.cache_ttl)
        return result

    def generate_structured(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model: str = None,
        temperature: float = 0.2,
        cache_key: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate structured JSON output from Gemini.
        Uses response_mime_type=application/json for reliable parsing.
        
        Returns:
            Parsed dict, or None on failure
        """
        text = self.generate_text(
            prompt=prompt,
            system_instruction=system_instruction,
            model=model,
            temperature=temperature,
            max_output_tokens=2048,
            response_mime_type="application/json",
            cache_key=cache_key,
        )
        if not text:
            return None

        # Parse JSON from response (handle markdown code blocks)
        try:
            text_clean = text.strip()
            if text_clean.startswith("```"):
                # Extract JSON from markdown code block
                lines = text_clean.split("\n")
                json_lines = []
                in_code = False
                for line in lines:
                    if line.startswith("```"):
                        in_code = not in_code
                        continue
                    if in_code:
                        json_lines.append(line)
                text_clean = "\n".join(json_lines)
            return json.loads(text_clean)
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse Gemini JSON response: %s", e)
            # Try to extract JSON from text
            import re
            match = re.search(r'\{.*\}', text_clean, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            return None

    def analyze_image(
        self,
        image_data: str,
        prompt: str,
        model: str = None,
        temperature: float = 0.2,
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze an image using Gemini Vision API.
        
        Args:
            image_data: Base64-encoded image data (with or without data:image/... prefix)
            prompt: Text prompt describing what to analyze
            model: Vision model (default: gemini-2.0-flash)
            
        Returns:
            Parsed JSON dict, or None on failure
        """
        model = model or self.MODEL_VISION
        url = self._build_url(model)

        # Strip data URI prefix if present
        if ',' in image_data:
            image_data = image_data.split(',')[1]

        mime_type = "image/jpeg"
        # Try to detect mime type from data
        if image_data.startswith('/9j/'):
            mime_type = "image/jpeg"
        elif image_data.startswith('iVBOR'):
            mime_type = "image/png"
        elif image_data.startswith('R0lGOD'):
            mime_type = "image/gif"
        elif image_data.startswith('UklGR'):
            mime_type = "image/webp"

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inlineData": {
                                "mimeType": mime_type,
                                "data": image_data
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 2048,
                "responseMimeType": "application/json",
            }
        }

        result = self._call_api(url, payload)
        if not result:
            return None

        try:
            return json.loads(result)
        except json.JSONDecodeError:
            logger.warning("Gemini vision response was not valid JSON")
            return None

    def count_tokens(self, text: str, model: str = None) -> int:
        """Count tokens for a given text (approximate)."""
        model = model or self.MODEL_TEXT
        url = self._build_url(model, "countTokens")
        payload = {"contents": [{"parts": [{"text": text}]}]}
        
        try:
            resp = requests.post(url, json=payload, headers=self._headers(), timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return data.get('totalTokens', 0)
        except Exception as e:
            logger.debug("Token counting failed: %s", e)
        return len(text) // 4  # Rough estimate

    def _call_api(self, url: str, payload: Dict) -> Optional[str]:
        """Make the actual API call with retry logic."""
        if not self.api_key:
            logger.warning("Gemini API key not configured")
            return None

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = requests.post(url, json=payload, headers=self._headers(), timeout=self.timeout)
                
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get('candidates', [])
                    if candidates:
                        parts = candidates[0].get('content', {}).get('parts', [])
                        if parts:
                            text = parts[0].get('text', '')
                            if text:
                                return text
                    logger.warning("Gemini returned empty response")
                    return None
                
                elif resp.status_code == 429:
                    # Rate limited
                    wait = min(2 ** attempt * 2, 30)
                    logger.warning("Gemini rate limited, retrying in %ds", wait)
                    time.sleep(wait)
                    last_error = f"Rate limited (429): {resp.text[:200]}"
                    continue
                
                elif resp.status_code == 403:
                    logger.error("Gemini API auth failed (403): %s", resp.text[:200])
                    return None
                
                elif resp.status_code == 400:
                    logger.error("Gemini API bad request (400): %s", resp.text[:300])
                    return None
                
                else:
                    logger.error("Gemini API error %d: %s", resp.status_code, resp.text[:200])
                    last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                    
            except requests.exceptions.Timeout:
                logger.warning("Gemini API timeout (attempt %d/%d)", attempt + 1, self.max_retries + 1)
                last_error = "Timeout"
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                    
            except requests.exceptions.ConnectionError as e:
                logger.warning("Gemini API connection error (attempt %d/%d): %s", attempt + 1, self.max_retries + 1, e)
                last_error = str(e)
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                    
            except Exception as e:
                logger.error("Gemini API unexpected error: %s", e)
                last_error = str(e)
                break

        logger.error("Gemini API failed after %d attempts: %s", self.max_retries + 1, last_error)
        return None


# Singleton instance
_client = None


def get_gemini_client() -> GeminiClient:
    """Get or create the singleton Gemini client."""
    global _client
    if _client is None:
        _client = GeminiClient()
    return _client
