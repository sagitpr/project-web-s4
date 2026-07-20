"""
AI Product Description Generator.
Generates SEO-friendly product titles, descriptions, specifications, and keywords
using Gemini API based on product name, category, and optional image.
"""

import logging
from typing import Optional, Dict, Any, List
from django.core.cache import cache

from products.models import Product, Category
from .gemini_client import get_gemini_client

logger = logging.getLogger('django_backend.ai_services.description')


class AIProductDescriptionGenerator:
    """AI-powered product description generator."""

    def __init__(self):
        self.client = get_gemini_client()

    def generate_description(
        self,
        product_name: str,
        category_name: str = '',
        price: Optional[float] = None,
        unit: str = '',
        additional_info: str = '',
        image_data: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate complete product description including title, description, keywords."""
        cache_key = f'ai_desc:{product_name}:{category_name}:{price}'
        cached = cache.get(cache_key)
        if cached:
            return cached

        image_context = ""
        if image_data:
            # Use vision to analyze product image
            image_analysis = self.client.analyze_image(
                image_data,
                "Deskripsikan produk ini secara detail. Sebutkan jenis, warna, bentuk, ukuran, dan kondisi visual.",
                temperature=0.2,
            )
            if image_analysis:
                image_context = f"\nAnalisis Gambar: {image_analysis.get('analysis_summary', '')}\n"
                if 'detected_texts' in image_analysis:
                    image_context += f"Teks pada label: {', '.join(image_analysis.get('detected_texts', []))}\n"

        prompt = (
            f"Anda adalah AI penulis deskripsi produk untuk Warungio Marketplace.\n\n"
            f"Nama Produk: {product_name}\n"
            f"Kategori: {category_name or 'Umum'}\n"
            f"Harga: {'Rp ' + f'{price:,.0f}' if price else 'Tidak ditentukan'}\n"
            f"Satuan: {unit or 'pcs'}\n"
            f"{image_context}"
            f"{'Info Tambahan: ' + additional_info if additional_info else ''}\n\n"
            "Kembalikan JSON dengan format EXACT:\n"
            "{\n"
            '  "seo_title": "Judul produk optimal SEO (maks 60 karakter, Bahasa Indonesia)",\n'
            '  "description": "Deskripsi produk 2-3 paragraf dalam Bahasa Indonesia, informatif dan menarik",\n'
            '  "short_description": "Deskripsi singkat 1 kalimat (maks 150 karakter)",\n'
            '  "specifications": [{"name": "Nama spesifikasi", "value": "Nilai"}],\n'
            '  "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],\n'
            '  "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3"],\n'
            '  "benefits": ["Manfaat 1", "Manfaat 2", "Manfaat 3"],\n'
            '  "usage_tips": "Tips penggunaan atau penyimpanan (1 kalimat)",\n'
            '  "target_audience": "Target pembeli produk ini"\n'
            "}"
        )

        result = self.client.generate_structured(
            prompt=prompt,
            temperature=0.7,
            cache_key=cache_key,
        )

        if not result:
            result = self._default_description(product_name, category_name, price)

        cache.set(cache_key, result, 86400)  # Cache for 24 hours
        return result

    def _default_description(self, name: str, category: str, price: Optional[float]) -> Dict[str, Any]:
        price_str = f"Rp {price:,.0f}" if price else ""
        return {
            'seo_title': name[:60],
            'description': f"{name} berkualitas tersedia di Warungio. Dapatkan {name.lower()} segar dan berkualitas terbaik. "
                          f"Belanja kebutuhan {category.lower() if category else 'harian'} Anda dengan mudah dan cepat.",
            'short_description': f"{name} berkualitas, segar, dan harga terjangkau.",
            'specifications': [{'name': 'Nama Produk', 'value': name}],
            'keywords': [name.lower(), category.lower() if category else ''],
            'hashtags': ['#' + name.replace(' ', '')],
            'benefits': ['Kualitas terjamin', 'Harga terjangkau', 'Pengiriman cepat'],
            'usage_tips': 'Simpan di tempat yang sesuai untuk menjaga kualitas.',
            'target_audience': 'Semua kalangan',
        }

    def generate_bulk_descriptions(self, products: List[Dict]) -> List[Dict]:
        """Generate descriptions for multiple products in batch."""
        product_list = "\n".join([
            f"- {p['name']} (Kategori: {p.get('category', '')}, Harga: Rp {p.get('price', 0):,.0f})"
            for p in products
        ])

        prompt = (
            f"Anda adalah AI penulis deskripsi produk massal.\n"
            f"Generate deskripsi untuk produk-produk berikut:\n\n{product_list}\n\n"
            "Untuk setiap produk, kembalikan JSON array:\n"
            "[{\n"
            '  "product_name": "Nama produk",\n'
            '  "seo_title": "Judul SEO",\n'
            '  "description": "Deskripsi 2 paragraf",\n'
            '  "keywords": ["keyword1", "keyword2"]\n'
            "}]"
        )

        result = self.client.generate_structured(prompt=prompt, temperature=0.5)
        return result if result and isinstance(result, list) else []


def get_description_generator() -> AIProductDescriptionGenerator:
    return AIProductDescriptionGenerator()
