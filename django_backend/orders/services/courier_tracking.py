"""
Courier Tracking Service for Warungio — Hyperlocal Delivery.

ONLY supports hyperlocal methods:
- Gojek (GoSend)
- Grab (GrabExpress)
- Maxim Delivery
- Antar Sendiri (Mitra Antar Sendiri)

These ride-hailing / local delivery services do NOT have public tracking APIs.
All tracking data is mock / status-based from the Delivery model.
Results are cached in Redis (5 min TTL) to reduce DB queries.

Milestones include:
  - step: int (1-6) mapping to the buyer 6-step timeline:
      1 = Pesanan Dibuat
      2 = Diproses Penjual
      3 = Menunggu Penjemputan
      4 = Kurir Menjemput
      5 = Dalam Perjalanan
      6 = Pesanan Diterima
  - icon: string matching frontend SVG icon names
  - status: human-readable status description
  - time: ISO datetime string
  - is_current: whether this is the active milestone
"""

import hashlib
import logging
from datetime import datetime, timedelta

from django.core.cache import cache

logger = logging.getLogger(__name__)

TRACKING_CACHE_PREFIX = 'tracking'
TRACKING_CACHE_TTL = 60 * 5  # 5 minutes

# ── Hyperlocal courier display names ──
HYPELOCAL_COURIERS = {
    'gosend': 'GoSend',
    'grabexpress': 'GrabExpress',
    'maxim': 'Maxim Delivery',
    'antar_sendiri': 'Antar Sendiri',
}

# ── Status display labels in Bahasa ──
DELIVERY_STATUS_LABELS = {
    'menunggu_konfirmasi': 'Menunggu Konfirmasi',
    'diproses_penjual': 'Diproses Penjual',
    'menunggu_penjemputan': 'Menunggu Penjemputan',
    'kurir_menjemput': 'Kurir Menjemput',
    'dalam_perjalanan': 'Dalam Perjalanan',
    'pesanan_diterima': 'Pesanan Diterima',
    'dibatalkan': 'Dibatalkan',
}

# ── Icon names used by frontend ──
# 'package'    -> SVG package box
# 'check'      -> SVG checkmark
# 'clock'      -> SVG clock (no icon rendered, just text)
# 'motorcycle' -> SVG motorcycle / rider
# 'truck'      -> SVG delivery truck
# 'x'          -> SVG X mark

# ── Tracking history templates per delivery status ──
# Each entry maps to a buyer timeline step:
#   step 1: Pesanan Dibuat
#   step 2: Diproses Penjual
#   step 3: Menunggu Penjemputan
#   step 4: Kurir Menjemput
#   step 5: Dalam Perjalanan
#   step 6: Pesanan Diterima
TRACKING_HISTORY_TEMPLATES = {
    'menunggu_konfirmasi': [
        {'step': 1, 'status': 'Pesanan berhasil dibuat', 'icon': 'package'},
    ],
    'diproses_penjual': [
        {'step': 1, 'status': 'Pesanan berhasil dibuat', 'icon': 'package'},
        {'step': 2, 'status': 'Pesanan dikonfirmasi penjual', 'icon': 'package'},
    ],
    'menunggu_penjemputan': [
        {'step': 1, 'status': 'Pesanan berhasil dibuat', 'icon': 'package'},
        {'step': 2, 'status': 'Pesanan dikonfirmasi penjual', 'icon': 'package'},
        {'step': 3, 'status': 'Menunggu penjemputan kurir', 'icon': 'clock'},
    ],
    'kurir_menjemput': [
        {'step': 1, 'status': 'Pesanan berhasil dibuat', 'icon': 'package'},
        {'step': 2, 'status': 'Pesanan dikonfirmasi penjual', 'icon': 'package'},
        {'step': 3, 'status': 'Pesanan siap dijemput kurir', 'icon': 'clock'},
        {'step': 4, 'status': 'Kurir sedang menjemput pesanan', 'icon': 'motorcycle'},
    ],
    'dalam_perjalanan': [
        {'step': 1, 'status': 'Pesanan berhasil dibuat', 'icon': 'package'},
        {'step': 2, 'status': 'Pesanan dikonfirmasi penjual', 'icon': 'package'},
        {'step': 3, 'status': 'Pesanan siap dijemput kurir', 'icon': 'clock'},
        {'step': 4, 'status': 'Kurir sedang menjemput pesanan', 'icon': 'motorcycle'},
        {'step': 5, 'status': 'Pesanan dalam perjalanan', 'icon': 'truck'},
    ],
    'pesanan_diterima': [
        {'step': 1, 'status': 'Pesanan berhasil dibuat', 'icon': 'package'},
        {'step': 2, 'status': 'Pesanan dikonfirmasi penjual', 'icon': 'package'},
        {'step': 3, 'status': 'Pesanan siap dijemput kurir', 'icon': 'clock'},
        {'step': 4, 'status': 'Kurir sedang menjemput pesanan', 'icon': 'motorcycle'},
        {'step': 5, 'status': 'Pesanan dalam perjalanan', 'icon': 'truck'},
        {'step': 6, 'status': 'Pesanan telah diterima', 'icon': 'check'},
    ],
    'dibatalkan': [
        {'step': 1, 'status': 'Pesanan berhasil dibuat', 'icon': 'package'},
        {'step': 6, 'status': 'Pesanan dibatalkan', 'icon': 'x'},
    ],
}


def get_delivery_status_label(status_code):
    """Get human-readable label for delivery status code."""
    return DELIVERY_STATUS_LABELS.get(status_code, status_code)


def get_hyperlocal_tracking(delivery):
    """
    Generate tracking data for a hyperlocal delivery.

    Uses the delivery model's current status to build milestones
    with step numbers (1-6) matching the buyer timeline and icon
    names for the frontend SVG renderer.

    Args:
        delivery: Delivery model instance

    Returns:
        dict with tracking data including milestones with step/icon fields
    """
    if not delivery:
        return None

    status = delivery.delivery_status or 'menunggu_konfirmasi'
    now = datetime.now()

    # Build milestones based on current status
    history_template = TRACKING_HISTORY_TEMPLATES.get(status)
    if not history_template:
        history_template = [{
            'step': 1,
            'status': get_delivery_status_label(status),
            'icon': 'clock',
        }]

    milestones = []
    step_count = len(history_template)
    for i, entry in enumerate(history_template):
        # Calculate offset time: each step is ~30 min apart, latest being now
        offset_minutes = (step_count - i - 1) * 30
        ts = now - timedelta(minutes=offset_minutes)

        # Determine if this is the current (active) milestone
        # The last milestone is current unless the order is delivered or cancelled
        is_last = (i == step_count - 1)
        is_terminal = (status == 'pesanan_diterima' or status == 'dibatalkan')
        is_current = is_last and not is_terminal

        milestones.append({
            'step': entry['step'],
            'status': entry['status'],
            'icon': entry['icon'],
            'time': ts.isoformat(),
            'is_current': is_current,
        })

    # Determine overall status label for frontend compatibility
    if status == 'pesanan_diterima':
        overall = 'delivered'
    elif status == 'dalam_perjalanan':
        overall = 'on_delivery'
    elif status in ('kurir_menjemput', 'menunggu_penjemputan'):
        overall = 'picked_up'
    elif status == 'dibatalkan':
        overall = 'cancelled'
    else:
        overall = 'waiting'

    # Resolve shipping method name
    shipping_method_name = ''
    if delivery.shipping_method:
        shipping_method_name = delivery.shipping_method.name
    elif delivery.courier_name:
        shipping_method_name = delivery.courier_name

    # Simulate coordinates for on_delivery and kurir_menjemput
    latitude = None
    longitude = None
    if status in ('kurir_menjemput', 'dalam_perjalanan') and delivery.order.store:
        store_lat = delivery.order.store.latitude
        store_lng = delivery.order.store.longitude
        if store_lat is not None and store_lng is not None:
            offset = 0.0015 if status == 'dalam_perjalanan' else 0.0005
            latitude = float(store_lat) + offset
            longitude = float(store_lng) - offset

    return {
        'courier': shipping_method_name,
        'delivery_status': status,
        'delivery_status_label': get_delivery_status_label(status),
        'status': overall,
        'milestones': milestones,
        'driver_name': delivery.driver_name or '',
        'driver_phone': delivery.driver_phone or '',
        'pickup_code': delivery.pickup_code or '',
        'estimated_time': delivery.estimated_time or '',
        'estimated_pickup': delivery.estimated_pickup or '',
        'estimated_delivery': None,
        'latitude': latitude,
        'longitude': longitude,
        'source': 'hyperlocal',
    }


def _make_cache_key(delivery_id, status='menunggu_konfirmasi'):
    """Build cache key for a delivery tracking query."""
    raw = f'{TRACKING_CACHE_PREFIX}:delivery:{delivery_id}:{status}'
    hashed = hashlib.sha256(raw.encode()).hexdigest()[:32]
    return f'{TRACKING_CACHE_PREFIX}:{hashed}'


def clear_tracking_cache(delivery_id=None):
    """Clear tracking cache for a specific delivery or all."""
    if delivery_id:
        for status in DELIVERY_STATUS_LABELS:
            cache.delete(_make_cache_key(delivery_id, status))
        logger.info(f'Cleared tracking cache for delivery #{delivery_id}')
    else:
        try:
            cache.clear()
            logger.info('Cleared ALL cache entries.')
        except Exception as exc:
            logger.warning(f'Could not clear cache backend: {exc}')


def get_tracking_status(delivery):
    """
    Main entry point: get hyperlocal tracking status for a delivery.

    Results are cached for TRACKING_CACHE_TTL seconds.
    Skips cache if delivery status is terminal (delivered / cancelled)
    to ensure fresh data on status transitions.

    Args:
        delivery: Delivery model instance

    Returns:
        dict with tracking data or None if delivery is invalid
    """
    if not delivery:
        return None

    status = delivery.delivery_status or 'menunggu_konfirmasi'
    cache_key = _make_cache_key(delivery.id, status)

    # Skip cache for terminal statuses to pick up transition changes quickly
    is_terminal = status in ('pesanan_diterima', 'dibatalkan')

    if not is_terminal:
        cached = cache.get(cache_key)
        if cached is not None:
            return {**cached, '_cache_hit': True}

    # Generate tracking data
    result = get_hyperlocal_tracking(delivery)
    if result and not is_terminal:
        cache.set(cache_key, result, TRACKING_CACHE_TTL)

    return result
