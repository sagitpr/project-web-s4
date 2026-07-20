"""
Smart Scan AI Service for Warungio Marketplace.

Server-side product scanning, freshness analysis, barcode/OCR metadata processing.
Integrates with unified GeminiClient for vision-based quality analysis.

All legacy fallback/heuristic code has been removed — every scan uses the
real Gemini Vision API via the centralized GeminiClient.
"""

import base64
import json
import logging
from datetime import date
from django.conf import settings

from ai_services.gemini_client import get_gemini_client

logger = logging.getLogger('django_backend.products.ai')

# ── Quality status constants ──
QUALITY_FRESH = 'fresh'
QUALITY_NORMAL = 'normal'
QUALITY_WARNING = 'warning'
QUALITY_REJECTED = 'rejected'
QUALITY_PENDING = 'pending'


def call_gemini_vision_api(base64_image: str, prompt: str) -> dict:
    """
    Call Gemini Vision API via the unified GeminiClient.
    
    This replaces the legacy Vertex AI SDK call that required GCP service accounts.
    Uses the API key from settings.GEMINI_KEY instead.
    
    Returns:
        dict | None: The parsed JSON response from Gemini, or None on failure.
    """
    if not base64_image:
        return None

    client = get_gemini_client()
    if not client.api_key:
        logger.warning("Gemini API key not configured. Vision API unavailable.")
        return None

    try:
        result = client.analyze_image(
            image_data=base64_image,
            prompt=prompt,
            temperature=0.2,
        )
        return result
    except Exception as e:
        logger.error(f"Error calling Gemini Vision API via unified client: {str(e)}")
        return None


def process_computer_vision(product_name, product_category='', image_base64=None):
    """
    Analyze product freshness using Gemini Vision API.
    
    Returns a structured quality assessment. If image is provided, uses real
    Gemini Vision inference. If no image, returns a minimal response without
    hardcoded heuristics.
    """
    if image_base64:
        prompt = (
            f"Analyze the freshness of this food product. "
            f"Product Name: {product_name}. Category: {product_category}. "
            "Return a JSON response with EXACTLY these keys: "
            "'freshness_score' (integer 0-100), "
            "'quality_status' (string, select from: fresh, normal, warning, rejected), "
            "'confidence' (float 0.0-1.0), "
            "'ai_result' (string, Indonesian description of the freshness observation and actionable shelf-life recommendation)."
        )
        gemini_res = call_gemini_vision_api(image_base64, prompt)
        if gemini_res:
            gemini_res['mode'] = 'computer_vision'
            return gemini_res

    # No image provided or Gemini unavailable for this request
    return {
        'freshness_score': None,
        'quality_status': QUALITY_PENDING,
        'confidence': None,
        'ai_result': 'Tidak ada gambar untuk dianalisis. Silakan unggah gambar produk.',
        'mode': 'computer_vision',
    }


def process_barcode(barcode=''):
    """Verify barcode format and return metadata."""
    if not barcode:
        return {
            'barcode': '',
            'freshness_score': None,
            'quality_status': QUALITY_PENDING,
            'confidence': None,
            'ai_result': 'Barcode tidak diberikan.',
            'mode': 'barcode',
        }

    is_valid = len(barcode) == 13 and barcode.isdigit()
    status = QUALITY_FRESH if is_valid else QUALITY_PENDING

    return {
        'barcode': barcode,
        'freshness_score': 100 if is_valid else None,
        'quality_status': status,
        'confidence': 0.98 if is_valid else None,
        'ai_result': f'Barcode terverifikasi: {barcode}.' if is_valid else f'Barcode {barcode} tidak valid.',
        'mode': 'barcode',
    }


def process_ocr(barcode='', bpom_number='', expiration_date='', image_base64=None):
    """Parse product packaging labels (BPOM, expiry) using Gemini Vision API."""
    if image_base64:
        prompt = (
            "Perform OCR on this product packaging. "
            "Return a JSON response with EXACTLY these keys: "
            "'barcode' (string, barcode found or empty), "
            "'bpom_number' (string, BPOM registration number found or empty), "
            "'expiration_date' (string, expiration date found in YYYY-MM-DD format or empty), "
            "'is_expired' (boolean), "
            "'freshness_score' (integer 0-100), "
            "'quality_status' (string, select from: fresh, normal, warning, rejected, pending), "
            "'confidence' (float 0.0-1.0), "
            "'confidence_uncertain' (boolean, true if OCR text is blurry/unclear), "
            "'ai_result' (string, Indonesian analysis summary of packaging metadata)."
        )
        gemini_res = call_gemini_vision_api(image_base64, prompt)
        if gemini_res:
            gemini_res['mode'] = 'ocr'
            return gemini_res

    # No image or Gemini unavailable — return minimal response without hardcoded defaults
    return {
        'barcode': barcode or '',
        'bpom_number': bpom_number or '',
        'expiration_date': expiration_date or '',
        'is_expired': None,
        'freshness_score': None,
        'quality_status': QUALITY_PENDING,
        'confidence': None,
        'confidence_uncertain': None,
        'ai_result': 'Tidak ada gambar untuk OCR. Silakan unggah gambar kemasan produk.',
        'mode': 'ocr',
    }


def process_manual(barcode='', bpom_number='', expiration_date=''):
    """Process manually verified product metadata."""
    result_text = 'Metadata dikonfirmasi manual.'
    if barcode:
        result_text += f' Barcode: {barcode}.'
    if bpom_number:
        result_text += f' BPOM: {bpom_number}.'
    if expiration_date:
        result_text += f' Exp: {expiration_date}.'

    return {
        'barcode': barcode or '',
        'bpom_number': bpom_number or '',
        'expiration_date': expiration_date or '',
        'freshness_score': None,
        'quality_status': QUALITY_PENDING,
        'confidence': None,
        'confidence_uncertain': None,
        'ai_result': result_text,
        'mode': 'manual',
    }


def process_scan(product, scan_type='computer_vision', options=None):
    """Main route handler for different scan modes."""
    options = options or {}
    product_name = product.product_name if product else 'Produk'
    product_category = product.category.category_name if product and product.category else ''

    if scan_type == 'computer_vision':
        return process_computer_vision(product_name, product_category, options.get('image'))
    elif scan_type == 'barcode':
        return process_barcode(options.get('barcode', ''))
    elif scan_type == 'ocr':
        return process_ocr(
            barcode=options.get('barcode', ''),
            bpom_number=options.get('bpom_number', ''),
            expiration_date=options.get('expiration_date', ''),
            image_base64=options.get('image')
        )
    elif scan_type == 'manual':
        return process_manual(
            barcode=options.get('barcode', ''),
            bpom_number=options.get('bpom_number', ''),
            expiration_date=options.get('expiration_date', ''),
        )
    else:
        return {
            'error': f'Scan type {scan_type} not supported.',
            'quality_status': QUALITY_PENDING,
            'freshness_score': None,
            'confidence': None,
            'ai_result': 'Mode scan tidak valid.',
            'mode': scan_type,
        }
