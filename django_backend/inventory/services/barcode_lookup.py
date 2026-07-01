"""
Barcode lookup service for Warungio inventory system.

Searches the MasterProduct database by barcode number.
If not found locally, attempts external API lookup (Open Food Facts, etc.)
and auto-creates a new MasterProduct record.

Supports EAN-13, EAN-8, and UPC-A barcode formats.
"""

import json
import logging
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from django.conf import settings

from ..models import MasterProduct

logger = logging.getLogger('django_backend.inventory.barcode')


BARCODE_EAN13 = 'ean13'
BARCODE_EAN8 = 'ean8'
BARCODE_UPCA = 'upca'


def detect_barcode_format(barcode: str) -> str | None:
    """Detect barcode format from length."""
    cleaned = barcode.strip()
    if not cleaned.isdigit():
        return None
    length = len(cleaned)
    if length == 13:
        return BARCODE_EAN13
    elif length == 8:
        return BARCODE_EAN8
    elif length == 12:
        return BARCODE_UPCA
    return None


def validate_barcode_checksum(barcode: str) -> bool:
    """
    Validate EAN-13 checksum digit.
    The last digit is a check digit calculated from the first 12 digits.
    """
    if not barcode or not barcode.isdigit():
        return False
    length = len(barcode)
    if length not in (8, 12, 13):
        return False
    # For EAN-13 (13 digits) or EAN-8 (8 digits), validate check digit
    if length in (8, 13):
        digits = [int(d) for d in barcode]
        check = digits.pop()
        total = 0
        for i, d in enumerate(digits):
            weight = 3 if (i % 2 == 0 if length == 13 else i % 2 == 1) else 1
            total += d * weight
        expected = (10 - (total % 10)) % 10
        return check == expected
    # UPC-A (12 digits) — no check digit validation (just format)
    return True


def lookup_barcode(barcode: str, store=None) -> dict:
    """
    Look up a barcode in the MasterProduct database.
    
    If found locally, returns the cached product info.
    If not found, attempts external lookup via Open Food Facts API.
    
    Args:
        barcode: 13-digit EAN-13 barcode string
        store: Optional Store instance for context
        
    Returns:
        dict with:
            - found: bool
            - master_product: MasterProduct dict or None
            - source: 'local', 'external', 'error'
            - error: error message if any
    """
    cleaned = barcode.strip()
    fmt = detect_barcode_format(cleaned)

    if not fmt:
        return {
            'found': False,
            'error': 'Format barcode tidak dikenal. Gunakan EAN-13 (13 digit) atau EAN-8 (8 digit).',
            'source': 'error',
        }

    # Check local database first
    try:
        master = MasterProduct.objects.filter(
            barcode=cleaned, is_active=True
        ).first()
        if master:
            return {
                'found': True,
                'master_product': _master_to_dict(master),
                'source': 'local',
            }
    except Exception as e:
        logger.warning('Local barcode lookup error: %s', e)

    # Not found locally — try external API
    try:
        result = _lookup_external(cleaned)
        if result.get('found'):
            # Auto-create new MasterProduct for future lookups
            try:
                master = _create_from_external(result['product_data'])
                return {
                    'found': True,
                    'master_product': _master_to_dict(master),
                    'source': 'external',
                    'is_new': True,
                }
            except Exception as e:
                logger.warning('Failed to create MasterProduct from external data: %s', e)
                return {
                    'found': True,
                    'master_product': result['product_data'],
                    'source': 'external',
                    'note': 'Gagal menyimpan ke database lokal.',
                }
        else:
            return result
    except Exception as e:
        logger.error('External barcode lookup error: %s', e)
        return {
            'found': False,
            'error': 'Barcode tidak ditemukan di database lokal maupun eksternal.',
            'source': 'error',
        }


def _lookup_external(barcode: str) -> dict:
    """
    Look up barcode via Open Food Facts API.
    Returns product data if found.
    """
    url = f'https://world.openfoodfacts.org/api/v2/product/{barcode}.json'

    try:
        req = Request(url, headers={'User-Agent': 'Warungio - v1.0'})
        with urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))

        if data.get('status') == 1 and data.get('product'):
            product = data['product']
            return {
                'found': True,
                'product_data': {
                    'barcode': barcode,
                    'product_name': product.get('product_name', ''),
                    'brand': product.get('brands', ''),
                    'category': _extract_category(product),
                    'subcategory': '',
                    'unit': _detect_unit(product),
                    'weight_value': _extract_weight(product),
                    'weight_unit': _extract_weight_unit(product),
                    'image_url': product.get('image_url', ''),
                    'manufacturer': product.get('manufacturer', ''),
                },
            }

        return {'found': False, 'error': 'Produk tidak ditemukan di database Open Food Facts.', 'source': 'external'}

    except HTTPError as e:
        if e.code == 404:
            return {'found': False, 'error': 'Barcode tidak ditemukan.', 'source': 'external'}
        return {'found': False, 'error': f'Error API: {e.code}', 'source': 'external'}
    except (URLError, TimeoutError) as e:
        return {'found': False, 'error': 'Gagal terhubung ke database produk.', 'source': 'external'}
    except json.JSONDecodeError:
        return {'found': False, 'error': 'Data produk tidak valid.', 'source': 'external'}


def _extract_category(product: dict) -> str:
    """Extract readable category from Open Food Facts data."""
    categories = product.get('categories', '')
    if categories:
        # Take the first meaningful category
        cats = [c.strip() for c in categories.split(',') if c.strip()]
        if cats:
            return cats[0]
    return 'Umum'


def _extract_weight(product: dict) -> float | None:
    """Extract product weight/quantity from Open Food Facts data."""
    qty = product.get('product_quantity', 0)
    return float(qty) if qty else None


def _extract_weight_unit(product: dict) -> str:
    """Extract weight unit."""
    return product.get('product_quantity_unit', 'g')


def _detect_unit(product: dict) -> str:
    """Detect appropriate unit from product data."""
    unit_map = {
        'g': 'g', 'gram': 'g', 'grams': 'g',
        'kg': 'kg', 'kilogram': 'kg', 'kilograms': 'kg',
        'ml': 'ml', 'milliliter': 'ml', 'millilitre': 'ml',
        'l': 'liter', 'liter': 'liter', 'liters': 'liter',
        'pcs': 'pcs', 'piece': 'pcs', 'pieces': 'pcs',
    }
    raw_unit = _extract_weight_unit(product)
    return unit_map.get(raw_unit.lower(), 'pcs')


def _create_from_external(product_data: dict) -> MasterProduct:
    """Create a MasterProduct record from external API data."""
    master = MasterProduct.objects.create(
        barcode=product_data['barcode'],
        product_name=product_data.get('product_name', 'Produk Tidak Diketahui')[:200],
        brand=product_data.get('brand', '')[:100],
        category=product_data.get('category', 'Umum')[:100],
        subcategory=product_data.get('subcategory', '')[:100],
        unit=product_data.get('unit', 'pcs'),
        weight_value=product_data.get('weight_value'),
        weight_unit=product_data.get('weight_unit', ''),
        image_url=product_data.get('image_url', ''),
        manufacturer=product_data.get('manufacturer', '')[:200],
    )
    logger.info('Created MasterProduct %s from external lookup', master.barcode)
    return master


def _master_to_dict(master: MasterProduct) -> dict:
    """Convert MasterProduct instance to dict for API response."""
    return {
        'id': master.id,
        'barcode': master.barcode,
        'product_name': master.product_name,
        'brand': master.brand,
        'category': master.category,
        'subcategory': master.subcategory,
        'unit': master.unit,
        'weight_value': float(master.weight_value) if master.weight_value else None,
        'weight_unit': master.weight_unit,
        'image_url': master.image_url,
        'manufacturer': master.manufacturer,
        'bpom_number': master.bpom_number,
    }
