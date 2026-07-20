"""
AI Vision Service — Product image analysis using Gemini Vision API.
OCR, freshness detection, label scanning, packaging analysis.
"""

import logging
from typing import Optional, Dict, Any
from django.conf import settings

from .gemini_client import get_gemini_client

logger = logging.getLogger('django_backend.ai_services.vision')


class AIVisionService:
    """
    AI-powered vision analysis for products.
    
    Features:
    - OCR: Extract text from product labels (BPOM, expiry, barcode, ingredients)
    - Freshness Detection: Analyze fruits, vegetables, meat, fish quality
    - Nutrition Facts: Extract and analyze nutrition information
    - Product Classification: Identify product type from image
    - Damage Detection: Detect packaging damage or defects
    """

    def __init__(self):
        self.client = get_gemini_client()

    def analyze_product_image(self, image_data: str, product_name: str = '') -> Dict[str, Any]:
        """
        Comprehensive product image analysis.
        Combines OCR, freshness, and quality checks in a single API call.
        """
        prompt = (
            f"Anda adalah AI analis produk untuk Warungio Marketplace.\n"
            f"Analisis gambar produk ini secara menyeluruh.\n\n"
            f"Nama Produk: {product_name or 'Tidak diketahui'}\n\n"
            "Kembalikan JSON dengan format EXACT:\n"
            "{\n"
            '  "product_type": "Jenis produk dari gambar",\n'
            '  "is_fresh_product": true/false,\n'
            '  "freshness_analysis": {\n'
            '    "freshness_score": 0-100,\n'
            '    "quality_status": "fresh|normal|warning|rejected",\n'
            '    "visual_indicators": ["Indicator 1", "Indicator 2"],\n'
            '    "recommendation": "Rekomendasi penyimpanan/penjualan"\n'
            '  },\n'
            '  "ocr_results": {\n'
            '    "detected_text": ["Teks yang terdeteksi"],\n'
            '    "bpom_number": "Nomor BPOM atau null",\n'
            '    "expiration_date": "Tanggal kadaluwarsa YYYY-MM-DD atau null",\n'
            '    "barcode": "Barcode terdeteksi atau null",\n'
            '    "ingredients": ["Bahan-bahan"],\n'
            '    "nutrition_info": {"kalori": null, "protein": null, "lemak": null},\n'
            '    "is_expired": true/false,\n'
            '    "ocr_confidence": 0.0-1.0\n'
            '  },\n'
            '  "packaging_quality": {\n'
            '    "damage_detected": true/false,\n'
            '    "damage_type": "Penyok|Sobek|Bocor|null",\n'
            '    "seal_intact": true/false\n'
            '  },\n'
            '  "confidence": 0.0-1.0,\n'
            '  "analysis_summary": "Ringkasan analisis dalam Bahasa Indonesia (maks 2 kalimat)"\n'
            "}"
        )

        result = self.client.analyze_image(image_data, prompt)
        if not result:
            return self._default_analysis()

        # Ensure all keys exist
        result.setdefault('product_type', 'Produk')
        result.setdefault('is_fresh_product', False)
        result.setdefault('freshness_analysis', {
            'freshness_score': 50,
            'quality_status': 'pending',
            'visual_indicators': [],
            'recommendation': 'Analisis membutuhkan gambar yang lebih jelas.'
        })
        result.setdefault('ocr_results', {
            'detected_text': [],
            'bpom_number': None,
            'expiration_date': None,
            'barcode': None,
            'ingredients': [],
            'nutrition_info': {},
            'is_expired': False,
            'ocr_confidence': 0.0
        })
        result.setdefault('packaging_quality', {
            'damage_detected': False,
            'damage_type': None,
            'seal_intact': True
        })
        result.setdefault('confidence', 0.5)
        result.setdefault('analysis_summary', 'Analisis produk selesai.')
        result['mode'] = 'computer_vision'

        return result

    def analyze_freshness(self, image_data: str, product_name: str = '') -> Dict[str, Any]:
        """
        Analyze product freshness using Gemini Vision.
        Specialized for fruits, vegetables, meat, fish.
        """
        prompt = (
            f"Anda adalah AI detektor kesegaran produk segar untuk Warungio Marketplace.\n"
            f"Analisis kesegaran produk ini dari gambar.\n\n"
            f"Nama Produk: {product_name or 'Produk Segar'}\n\n"
            "Kembalikan JSON dengan format EXACT:\n"
            "{\n"
            '  "product_type": "Jenis produk yang terdeteksi (buah/sayur/daging/ikan/lainnya)",\n'
            '  "freshness_score": 0-100,\n'
            '  "quality_status": "fresh|normal|warning|rejected",\n'
            '  "visual_indicators": ["Indikator visual seperti warna, tekstur, bercak"],\n'
            '  "color_analysis": "Analisis warna produk",\n'
            '  "texture_analysis": "Analisis tekstur dari visual",\n'
            '  "ripeness": "Tingkat kematangan untuk buah/sayur",\n'
            '  "confidence": 0.0-1.0,\n'
            '  "shelf_life_days": "Perkiraan hari tersisa sebelum tidak layak (angka atau null)",\n'
            '  "recommendation": "Rekomendasi penjualan dan penyimpanan dalam Bahasa Indonesia",\n'
            '  "ai_result": "Deskripsi observasi kesegaran dalam Bahasa Indonesia"\n'
            "}"
        )

        result = self.client.analyze_image(image_data, prompt)
        if not result:
            return self._default_freshness_analysis()

        result['mode'] = 'computer_vision'
        return result

    def scan_label(self, image_data: str) -> Dict[str, Any]:
        """
        OCR-focused analysis of product labels.
        Extracts BPOM number, expiry date, barcode, ingredients.
        """
        prompt = (
            "Anda adalah AI OCR untuk label produk Indonesia.\n"
            "Ekstrak informasi dari label produk ini.\n\n"
            "Kembalikan JSON dengan format EXACT:\n"
            "{\n"
            '  "detected_texts": ["Semua teks yang terdeteksi dari label"],\n'
            '  "bpom_number": "Nomor BPOM/BPOM RI atau null (format: MD/MD [nomor])",\n'
            '  "expiration_date": "Tanggal kadaluwarsa dalam YYYY-MM-DD atau null",\n'
            '  "production_date": "Tanggal produksi dalam YYYY-MM-DD atau null",\n'
            '  "barcode": "Kode barcode EAN-13 atau null",\n'
            '  "product_name_on_label": "Nama produk pada kemasan",\n'
            '  "brand": "Merek produk",\n'
            '  "net_weight": "Berat bersih (contoh: 500g, 1kg, 100ml)",\n'
            '  "ingredients": ["Daftar bahan-bahan"],\n'
            '  "is_halal": true/false/null,\n'
            '  "is_expired": true/false,\n'
            '  "ocr_confidence": 0.0-1.0,\n'
            '  "ai_result": "Ringkasan informasi label dalam Bahasa Indonesia"\n'
            "}"
        )

        result = self.client.analyze_image(image_data, prompt)
        if not result:
            return self._default_label_scan()

        result['mode'] = 'ocr'
        return result

    def _default_analysis(self) -> Dict[str, Any]:
        return {
            'product_type': 'Produk',
            'is_fresh_product': False,
            'freshness_analysis': {
                'freshness_score': 50,
                'quality_status': 'pending',
                'visual_indicators': [],
                'recommendation': 'Gambar tidak tersedia untuk analisis.'
            },
            'ocr_results': {
                'detected_text': [],
                'bpom_number': None,
                'expiration_date': None,
                'barcode': None,
                'ingredients': [],
                'nutrition_info': {},
                'is_expired': False,
                'ocr_confidence': 0.0
            },
            'packaging_quality': {
                'damage_detected': False,
                'damage_type': None,
                'seal_intact': True
            },
            'confidence': 0.0,
            'analysis_summary': 'Gambar produk tidak tersedia untuk analisis AI.',
            'mode': 'computer_vision',
        }

    def _default_freshness_analysis(self) -> Dict[str, Any]:
        return {
            'product_type': 'unknown',
            'freshness_score': 50,
            'quality_status': 'pending',
            'visual_indicators': [],
            'color_analysis': 'Gambar tidak tersedia',
            'texture_analysis': 'Gambar tidak tersedia',
            'ripeness': 'unknown',
            'confidence': 0.0,
            'shelf_life_days': None,
            'recommendation': 'Gambar tidak tersedia. Gunakan pengecekan manual.',
            'ai_result': 'Tidak dapat menganalisis kesegaran tanpa gambar.',
            'mode': 'computer_vision',
        }

    def _default_label_scan(self) -> Dict[str, Any]:
        return {
            'detected_texts': [],
            'bpom_number': None,
            'expiration_date': None,
            'production_date': None,
            'barcode': None,
            'product_name_on_label': None,
            'brand': None,
            'net_weight': None,
            'ingredients': [],
            'is_halal': None,
            'is_expired': False,
            'ocr_confidence': 0.0,
            'ai_result': 'Gambar label tidak tersedia untuk OCR.',
            'mode': 'ocr',
        }


def get_vision_service() -> AIVisionService:
    return AIVisionService()
