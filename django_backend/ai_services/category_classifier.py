"""
AI Smart Category Classification.
Automatically categorizes products using image analysis and product descriptions
via Gemini API.
"""

import logging
from typing import Optional, Dict, Any
from django.core.cache import cache

from products.models import Category
from .gemini_client import get_gemini_client

logger = logging.getLogger('django_backend.ai_services.category')


class AICategoryClassifier:
    """
    AI-powered product category classification.
    Uses product name, description, and optional image to suggest best categories.
    """

    def __init__(self):
        self.client = get_gemini_client()

    def classify(
        self,
        product_name: str,
        description: str = '',
        image_data: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Classify product and suggest the best categories.
        
        Returns:
            Dict with suggested category and confidence score
        """
        # Get available categories from database
        categories = Category.objects.filter(is_active=True)
        category_list = "\n".join([
            f"- {c.category_name}" + (f" ({c.description})" if c.description else "")
            for c in categories
        ])

        if not categories:
            return {
                'suggested_category': None,
                'confidence': 0,
                'all_suggestions': [],
                'error': 'Tidak ada kategori yang tersedia.',
            }

        # Build prompt with or without image
        if image_data:
            return self._classify_with_image(product_name, description, category_list, image_data)
        else:
            return self._classify_text_only(product_name, description, category_list)

    def _classify_text_only(
        self,
        product_name: str,
        description: str,
        category_list: str,
    ) -> Dict[str, Any]:
        """Classify using text only."""
        prompt = (
            f"Anda adalah AI klasifikasi produk untuk Warungio Marketplace.\n\n"
            f"Nama Produk: {product_name}\n"
            f"Deskripsi: {description or 'Tidak ada deskripsi'}\n\n"
            f"Kategori yang tersedia:\n{category_list}\n\n"
            "Pilih kategori yang PALING SESUAI untuk produk ini berdasarkan nama dan deskripsinya.\n\n"
            "Kembalikan JSON:\n"
            "{\n"
            '  "suggested_category": "Nama kategori yang paling sesuai",\n'
            '  "confidence": 0.0-1.0,\n'
            '  "reason": "Alasan pemilihan kategori dalam Bahasa Indonesia",\n'
            '  "all_suggestions": [{"category": "Kategori 1", "confidence": 0.0-1.0, "reason": "Alasan"}],\n'
            '  "alternative_categories": ["Kategori alternatif 1", "Kategori alternatif 2"]\n'
            "}"
        )

        return self._parse_classification(prompt, product_name)

    def _classify_with_image(
        self,
        product_name: str,
        description: str,
        category_list: str,
        image_data: str,
    ) -> Dict[str, Any]:
        """Classify using both text and image."""
        prompt = (
            f"Anda adalah AI klasifikasi produk untuk Warungio Marketplace.\n\n"
            f"Nama Produk: {product_name}\n"
            f"Deskripsi: {description or 'Tidak ada deskripsi'}\n\n"
            f"Kategori yang tersedia:\n{category_list}\n\n"
            "Analisis gambar produk dan pilih kategori yang PALING SESUAI.\n"
            "Gunakan informasi visual dari gambar untuk menentukan kategori.\n\n"
            "Kembalikan JSON:\n"
            "{\n"
            '  "suggested_category": "Nama kategori yang paling sesuai",\n'
            '  "confidence": 0.0-1.0,\n'
            '  "reason": "Alasan pemilihan kategori dalam Bahasa Indonesia",\n'
            '  "visual_observations": ["Observasi visual 1", "Observasi visual 2"],\n'
            '  "all_suggestions": [{"category": "Kategori 1", "confidence": 0.0-1.0}],\n'
            '  "alternative_categories": ["Kategori alternatif 1", "Kategori alternatif 2"]\n'
            "}"
        )

        result = self.client.analyze_image(image_data, prompt)
        if not result:
            return self._classify_text_only(product_name, description, category_list)

        return result

    def _parse_classification(self, prompt: str, product_name: str) -> Dict[str, Any]:
        """Parse Gemini classification response."""
        cache_key = f'ai_classify:{product_name.lower()[:50]}'
        result = self.client.generate_structured(prompt=prompt, temperature=0.2, cache_key=cache_key)

        if result and result.get('suggested_category'):
            return result

        return {
            'suggested_category': None,
            'confidence': 0,
            'reason': 'Gagal mengklasifikasikan produk secara otomatis.',
            'all_suggestions': [],
            'alternative_categories': [],
        }

    def batch_classify(self, products: list) -> list:
        """Classify multiple products at once."""
        if not products:
            return []

        product_list = "\n".join([
            f"- {p.get('name', 'Unknown')}: {p.get('description', '')[:100]}"
            for p in products
        ])

        prompt = (
            f"Anda adalah AI klasifikasi produk massal.\n"
            f"Klasifikasikan setiap produk ke dalam kategori yang sesuai.\n\n"
            f"Produk:\n{product_list}\n\n"
            "Kembalikan JSON array:\n"
            "[{\"product_name\": \"Nama\", \"suggested_category\": \"Kategori\", \"confidence\": 0.9}]"
        )

        result = self.client.generate_structured(prompt=prompt, temperature=0.2)
        return result if isinstance(result, list) else []


def get_category_classifier() -> AICategoryClassifier:
    return AICategoryClassifier()
