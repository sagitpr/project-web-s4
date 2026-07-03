"""
Binderbyte API Service for Warungio Marketplace.

Binderbyte provides Indonesian-focused APIs:
  - Tracking API: Track shipments for JNE, J&T, Pos Indonesia, SiCepat, etc.
  - Wilayah API: Province/City/District/Village data from Kemendagri
  - Geocoding API: Convert address to coordinates

API docs: https://docs.binderbyte.com
Get API key: https://binderbyte.com
"""

import logging
import hashlib
from typing import Optional, Dict, List, Any

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Cache TTLs
TRACKING_CACHE_TTL = 60 * 5        # 5 min — active tracking
REGIONS_CACHE_TTL = 60 * 60 * 24   # 24h — regional data rarely changes
GEOCODE_CACHE_TTL = 60 * 60 * 24 * 7  # 7 days — geocode results stable

CACHE_PREFIX = 'binderbyte'

# ── Status mapping: Binderbyte → Warungio internal ──
STATUS_MAP = {
    'DELIVERED':       'pesanan_diterima',
    'ON_PROGRESS':     'dalam_perjalanan',
    'PACKING':         'diproses_penjual',
    'SHIPPING':        'dalam_perjalanan',
    'TRANSIT':         'dalam_perjalanan',
    'DELIVERY':        'dalam_perjalanan',
    'PICKUP':          'kurir_menjemput',
    'HOLD':            'diproses_penjual',
    'CANCELLED':       'dibatalkan',
    'WAITING':         'menunggu_penjemputan',
}

STATUS_LABEL_MAP = {
    'pesanan_diterima':     'Pesanan Diterima',
    'dalam_perjalanan':     'Dalam Perjalanan',
    'diproses_penjual':     'Diproses Penjual',
    'kurir_menjemput':      'Kurir Menjemput',
    'menunggu_penjemputan': 'Menunggu Penjemputan',
    'dibatalkan':           'Dibatalkan',
}

# ── Couriers supported by Binderbyte ──
SUPPORTED_COURIERS = [
    'jne', 'jnt', 'pos', 'sicepat', 'tiki', 'wahana',
    'lion', 'ninja', 'jet', 'rex', 'ide', 'sap', 'pandu',
    'first', 'cahaya', 'star', 'ncs', 'central', 'slis',
    'spx', 'sentral', 'dse', 'db',
]


def _make_cache_key(*parts: str) -> str:
    """Build hashed cache key to avoid key length issues."""
    raw = ':'.join([CACHE_PREFIX] + list(parts))
    return f'{CACHE_PREFIX}:{hashlib.sha256(raw.encode()).hexdigest()[:32]}'


def is_binderbyte_available() -> bool:
    """Check if Binderbyte API key is configured."""
    return bool(settings.BINDERBYTE_API_KEY)


def is_national_courier(courier_slug: str) -> bool:
    """Check if a courier slug is a national courier (Binderbyte-supported)."""
    return courier_slug.lower().strip() in SUPPORTED_COURIERS


# =============================================================================
# COURIER TRACKING
# =============================================================================

def track_shipment(awb: str, courier: str) -> Optional[Dict[str, Any]]:
    """
    Track a shipment via Binderbyte API.
    
    Args:
        awb: Air Waybill number (e.g., 'JP1234567890')
        courier: Courier code (e.g., 'jne', 'jnt', 'sicepat')
    
    Returns:
        dict with tracking data or None if failed
    
    Note: Requires BINDERBYTE_API_KEY to be set in .env
    """
    api_key = settings.BINDERBYTE_API_KEY
    if not api_key:
        logger.warning('BINDERBYTE_API_KEY not set — cannot track shipment')
        return None
    
    cache_key = _make_cache_key('track', courier, awb)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    url = f'{settings.BINDERBYTE_BASE_URL}/track'
    params = {
        'api_key': api_key,
        'courier': courier.lower(),
        'awb': awb,
    }
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        if data.get('error'):
            logger.error('Binderbyte tracking error for %s/%s: %s', courier, awb, data.get('message'))
            return None
        
        # Transform to Warungio internal format
        result = _transform_tracking_data(data, courier, awb)
        cache.set(cache_key, result, TRACKING_CACHE_TTL)
        return result
    
    except requests.RequestException as e:
        logger.error('Binderbyte tracking request failed: %s', str(e))
        return None


def _transform_tracking_data(raw: dict, courier: str, awb: str) -> dict:
    """Transform Binderbyte raw tracking response to Warungio format."""
    data = raw.get('data', {})
    history = data.get('history', [])
    
    # Determine latest status
    latest_status = raw.get('status', '').upper()
    internal_status = STATUS_MAP.get(latest_status, 'dalam_perjalanan')
    
    milestones = []
    total = len(history)
    for i, h in enumerate(reversed(history)):
        # i=0 is the LATEST event (reversed[0] = history[-1])
        ts = h.get('date', '') if h.get('date') else ''
        desc = h.get('desc', h.get('description', ''))
        step = min(i + 1, 6)
        
        is_current = (i == 0) and internal_status not in ('pesanan_diterima', 'dibatalkan')
        
        milestones.append({
            'step': step,
            'status': desc,
            'icon': 'truck' if 'jalan' in desc.lower() else 'package',
            'time': ts,
            'is_current': is_current,
        })
    
    # If delivered, mark last milestone as check
    if internal_status == 'pesanan_diterima' and milestones:
        milestones[-1]['icon'] = 'check'
    
    # Courier display name
    courier_names = {
        'jne': 'JNE', 'jnt': 'J&T Express', 'pos': 'Pos Indonesia',
        'sicepat': 'SiCepat', 'tiki': 'TIKI', 'wahana': 'Wahana',
    }
    courier_name = courier_names.get(courier.lower(), courier.upper())
    
    # Overall status
    overall_map = {
        'pesanan_diterima': 'delivered',
        'dalam_perjalanan': 'on_delivery',
        'kurir_menjemput': 'picked_up',
        'menunggu_penjemputan': 'waiting',
        'diproses_penjual': 'processing',
        'dibatalkan': 'cancelled',
    }
    
    return {
        'courier': courier_name,
        'courier_code': courier.lower(),
        'awb': awb,
        'delivery_status': internal_status,
        'delivery_status_label': STATUS_LABEL_MAP.get(internal_status, internal_status),
        'status': overall_map.get(internal_status, 'waiting'),
        'milestones': milestones,
        'source': 'binderbyte',
        'origin': data.get('origin', data.get('from', '')),
        'destination': data.get('destination', data.get('to', '')),
        'driver_name': '',
        'driver_phone': '',
    }


# =============================================================================
# REGIONS / WILAYAH DATA (Province → City → District → Village)
# =============================================================================

def fetch_provinces() -> Optional[List[Dict]]:
    """Fetch all provinces from Binderbyte Wilayah API."""
    return _fetch_regions('province')


def fetch_regencies(province_code: str) -> Optional[List[Dict]]:
    """Fetch regencies/cities for a province."""
    return _fetch_regions('regency', province_code)


def fetch_districts(regency_code: str) -> Optional[List[Dict]]:
    """Fetch districts for a regency/city."""
    return _fetch_regions('district', regency_code)


def fetch_villages(district_code: str) -> Optional[List[Dict]]:
    """Fetch villages for a district."""
    return _fetch_regions('village', district_code)


def _fetch_regions(level: str, parent_code: str = '') -> Optional[List[Dict]]:
    """
    Generic Binderbyte Wilayah API caller.
    
    Args:
        level: 'province', 'regency', 'district', 'village'
        parent_code: Parent admin code (required for regency/district/village)
    
    Returns:
        list of region dicts with 'code', 'name' keys
    """
    api_key = settings.BINDERBYTE_API_KEY
    if not api_key:
        logger.warning('BINDERBYTE_API_KEY not set — cannot fetch regions')
        return None
    
    cache_key = _make_cache_key('region', level, parent_code or 'all')
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    url = f'{settings.BINDERBYTE_BASE_URL}/wilayah'
    params = {
        'api_key': api_key,
        'level': level,
    }
    if parent_code:
        params['parent_code'] = parent_code
    
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        
        if data.get('error'):
            logger.error('Binderbyte regions error for %s: %s', level, data.get('message'))
            return None
        
        result = data.get('data', data.get('value', []))
        cache.set(cache_key, result, REGIONS_CACHE_TTL)
        return result
    
    except requests.RequestException as e:
        logger.error('Binderbyte regions request failed: %s', str(e))
        return None


# =============================================================================
# FORWARD GEOCODING (Address → Coordinates)
# =============================================================================

def geocode_address(address: str, city: str = '') -> Optional[Dict[str, float]]:
    """
    Geocode an Indonesian address to coordinates via Binderbyte.
    
    Args:
        address: Full address string
        city: City name (optional, improves accuracy)
    
    Returns:
        dict with 'latitude', 'longitude' or None
    
    Note: Binderbyte geocoding is Indonesia-specific and often more accurate
    for Indonesian addresses than Google Geocoding API.
    """
    api_key = settings.BINDERBYTE_API_KEY
    if not api_key:
        return None
    
    cache_key = _make_cache_key('geocode', hashlib.md5(f'{address}:{city}'.encode()).hexdigest())
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    url = f'{settings.BINDERBYTE_BASE_URL}/geocode'
    params = {
        'api_key': api_key,
        'address': address,
    }
    if city:
        params['city'] = city
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        if data.get('error') or not data.get('data'):
            return None
        
        coords = data['data']
        result = {
            'latitude': float(coords.get('latitude', 0)),
            'longitude': float(coords.get('longitude', 0)),
        }
        
        if result['latitude'] and result['longitude']:
            cache.set(cache_key, result, GEOCODE_CACHE_TTL)
            return result
        
        return None
    
    except requests.RequestException as e:
        logger.error('Binderbyte geocode failed: %s', str(e))
        return None


# =============================================================================
# HEALTH CHECK
# =============================================================================

def check_health() -> dict:
    """Check Binderbyte API connectivity."""
    api_key = settings.BINDERBYTE_API_KEY
    if not api_key:
        return {'available': False, 'reason': 'BINDERBYTE_API_KEY not configured'}
    
    try:
        url = f'{settings.BINDERBYTE_BASE_URL}/province'
        resp = requests.get(url, params={'api_key': api_key}, timeout=5)
        if resp.ok:
            return {'available': True, 'status': 'ok'}
        return {'available': False, 'reason': f'HTTP {resp.status_code}'}
    except requests.RequestException as e:
        return {'available': False, 'reason': str(e)}
