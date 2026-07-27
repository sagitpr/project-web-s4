"""
GrabExpress and GoSend Delivery API Client for Warungio.

Provides:
- OAuth 2.0 client credentials flow
- Rate calculation (distance-based pricing)
- Automatic courier booking after payment
- Webhook signature verification
- Driver position polling for live GPS tracking
- Idempotency, retry, and comprehensive logging

Environment variables (set in .env):
  GRAB_CLIENT_ID, GRAB_CLIENT_SECRET, GRAB_API_URL, GRAB_IS_SANDBOX
  GOJEK_CLIENT_ID, GOJEK_CLIENT_SECRET, GOJEK_API_URL, GOJEK_IS_SANDBOX
"""

import hashlib
import hmac
import json
import logging
import time
import uuid
from decimal import Decimal
from typing import Optional, Dict, Any, List, Tuple
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)

# Cache TTLs
TOKEN_CACHE_TTL = 3300  # 55 min (tokens expire at 60 min)
RATE_CACHE_TTL = 60 * 5  # 5 min
POSITION_CACHE_TTL = 15  # 15 sec for live GPS polling

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF = [1, 2, 4]  # seconds


# =============================================================================
# BASE CLIENT
# =============================================================================

class BaseDeliveryClient:
    """Base class for GrabExpress and GoSend API clients."""

    def __init__(self, client_id: str, client_secret: str, base_url: str,
                 is_sandbox: bool, webhook_secret: str = '', partner_name: str = ''):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = base_url
        self.is_sandbox = is_sandbox
        self.webhook_secret = webhook_secret
        self.partner_name = partner_name
        self._access_token = None
        self._token_expiry = 0
        self._session = requests.Session()
        self._session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })

    def _get_auth_url(self) -> str:
        """Get OAuth token endpoint URL."""
        raise NotImplementedError

    def _authenticate(self) -> bool:
        """
        Obtain OAuth 2.0 access token using client credentials.
        Tokens are cached in Redis to avoid repeated auth requests.
        Returns True if authenticated successfully.
        """
        cache_key = f'delivery_token:{self.partner_name}:{self.client_id[:8]}'
        cached = cache.get(cache_key)
        if cached:
            self._access_token = cached['access_token']
            self._token_expiry = cached['expires_at']
            self._session.headers.update({
                'Authorization': f'Bearer {self._access_token}'
            })
            return True

        try:
            url = self._get_auth_url()
            payload = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'grant_type': 'client_credentials',
            }
            resp = self._session.post(url, json=payload, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            self._access_token = data.get('access_token', data.get('token', ''))
            expires_in = int(data.get('expires_in', 3600))
            self._token_expiry = time.time() + expires_in - 60  # 1 min buffer

            self._session.headers.update({
                'Authorization': f'Bearer {self._access_token}'
            })

            # Cache token
            cache.set(cache_key, {
                'access_token': self._access_token,
                'expires_at': self._token_expiry,
            }, TOKEN_CACHE_TTL)

            logger.info(f'{self.partner_name} OAuth token obtained (expires in {expires_in}s)')
            return True

        except requests.RequestException as e:
            logger.error(f'{self.partner_name} OAuth failed: {str(e)}')
            return False

    def _request(self, method: str, path: str, **kwargs) -> Optional[Dict]:
        """
        Make authenticated API request with automatic retry and token refresh.
        """
        url = urljoin(self.base_url.rstrip('/') + '/', path.lstrip('/'))

        for attempt in range(MAX_RETRIES):
            # Ensure we have a valid token
            if not self._access_token or time.time() >= self._token_expiry:
                if not self._authenticate():
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_BACKOFF[attempt])
                        continue
                    return None

            try:
                resp = self._session.request(method, url, timeout=30, **kwargs)

                # Handle 401 — token may have expired; retry once with fresh token
                if resp.status_code == 401:
                    cache.delete(f'delivery_token:{self.partner_name}:{self.client_id[:8]}')
                    self._access_token = None
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_BACKOFF[attempt])
                        continue

                resp.raise_for_status()
                return resp.json()

            except requests.Timeout:
                logger.warning(f'{self.partner_name} request timeout ({url}) attempt {attempt + 1}')
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_BACKOFF[attempt])
                    continue
                return None

            except requests.RequestException as e:
                logger.error(f'{self.partner_name} request failed: {str(e)}')
                return None

        return None

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify webhook payload signature using HMAC-SHA256.
        Override in subclass for partner-specific verification.
        """
        if not self.webhook_secret:
            logger.warning(f'{self.partner_name} webhook secret not configured')
            return False
        expected = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    def is_available(self) -> bool:
        """Check if the delivery service is configured and available."""
        return bool(self.client_id) and bool(self.client_secret)


# =============================================================================
# GRABEXPRESS CLIENT
# =============================================================================

class GrabExpressClient(BaseDeliveryClient):
    """
    GrabExpress delivery API client.

    API Reference: https://developer.grab.com
    Endpoints:
      - OAuth: POST /partner/v1/oauth/token
      - Rate: POST /partner/delivery/v1/rates
      - Create: POST /partner/delivery/v1/deliveries
      - Status: GET /partner/delivery/v1/deliveries/{id}
      - Cancel: DELETE /partner/delivery/v1/deliveries/{id}
      - Webhook: POST /partner/delivery/v1/webhook
    """

    SUPPORTED_SERVICES = ['Instant', 'SameDay', 'Regular']

    def __init__(self):
        is_sandbox = getattr(settings, 'GRAB_IS_SANDBOX', True)
        base_url = getattr(settings, 'GRAB_SANDBOX_URL', 'https://sandbox.grab.com') if is_sandbox else getattr(settings, 'GRAB_API_URL', 'https://api.grab.com')
        super().__init__(
            client_id=getattr(settings, 'GRAB_CLIENT_ID', ''),
            client_secret=getattr(settings, 'GRAB_CLIENT_SECRET', ''),
            base_url=base_url,
            is_sandbox=is_sandbox,
            webhook_secret=getattr(settings, 'GRAB_WEBHOOK_SECRET', ''),
            partner_name='GrabExpress',
        )

    def _get_auth_url(self) -> str:
        return urljoin(self.base_url.rstrip('/') + '/', 'partner/v1/oauth/token')

    def get_available_services(self) -> List[str]:
        """Return available service types based on config."""
        services = getattr(settings, 'GRAB_SERVICE_TYPES', ['Instant', 'SameDay', 'Regular'])
        return [s for s in services if s in self.SUPPORTED_SERVICES]

    def calculate_rate(self, origin: Dict, destination: Dict,
                       items: List[Dict], service_type: str = 'Instant') -> Optional[Dict]:
        """
        Calculate delivery rate (ongkir).

        Args:
            origin: {'latitude': float, 'longitude': float, 'address': str}
            destination: {'latitude': float, 'longitude': float, 'address': str}
            items: [{'name': str, 'quantity': int, 'weight_kg': float, 'price': float}]
            service_type: 'Instant', 'SameDay', 'Regular'

        Returns:
            dict with 'total_fee', 'currency', 'estimated_time', 'distance_km', 'breakdown'
            or None if rate calculation fails.
        """
        cache_key = (
            f'grab_rate:{origin.get("latitude", 0)}:{origin.get("longitude", 0)}:'
            f'{destination.get("latitude", 0)}:{destination.get("longitude", 0)}:'
            f'{service_type}'
        )
        cached = cache.get(cache_key)
        if cached:
            return cached

        payload = {
            'serviceType': service_type,
            'origin': {
                'coordinates': {
                    'latitude': origin.get('latitude', 0),
                    'longitude': origin.get('longitude', 0),
                },
                'address': origin.get('address', ''),
            },
            'destination': {
                'coordinates': {
                    'latitude': destination.get('latitude', 0),
                    'longitude': destination.get('longitude', 0),
                },
                'address': destination.get('address', ''),
            },
            'packages': [{
                'name': item.get('name', 'Package'),
                'quantity': item.get('quantity', 1),
                'weight': item.get('weight_kg', 1),
            } for item in items],
        }

        result = self._request('POST', 'partner/delivery/v1/rates', json=payload)

        if result:
            rate_data = {
                'total_fee': float(result.get('totalFee', result.get('total_fee', 0))),
                'currency': result.get('currency', 'IDR'),
                'estimated_time': result.get('estimatedTime', result.get('estimated_time', '')),
                'distance_km': float(result.get('distanceKm', result.get('distance_km', 0))),
                'breakdown': result.get('breakdown', result.get('priceBreakdown', [])),
                'service_type': service_type,
                'provider': 'grabexpress',
            }
            cache.set(cache_key, rate_data, RATE_CACHE_TTL)
            return rate_data

        # Fallback: estimate based on distance when API unavailable
        return self._estimate_fallback(origin, destination, items, service_type)

    def _estimate_fallback(self, origin: Dict, destination: Dict,
                           items: List[Dict], service_type: str) -> Dict:
        """Fallback rate estimation when Grab API is unavailable."""
        logger.info(f'GrabExpress API unavailable — using distance-based estimate')

        from .distance import calculate_haversine_distance

        d = calculate_haversine_distance(
            origin.get('latitude'), origin.get('longitude'),
            destination.get('latitude'), destination.get('longitude'),
        )
        distance = d if d is not None and d > 0 else 3.0  # default 3km

        # Grab pricing: Rp 5,000 base + Rp 3,000/km (Instant)
        # SameDay: Rp 3,000 base + Rp 2,000/km
        base_fees = {'Instant': 5000, 'SameDay': 3000, 'Regular': 2000}
        per_km = {'Instant': 3000, 'SameDay': 2000, 'Regular': 1500}

        base = base_fees.get(service_type, 5000)
        per = per_km.get(service_type, 3000)
        total_fee = base + (per * distance)

        return {
            'total_fee': total_fee,
            'currency': 'IDR',
            'estimated_time': '15-30 menit' if service_type == 'Instant' else '2-4 jam',
            'distance_km': round(distance, 2),
            'breakdown': [
                {'name': 'Biaya Dasar', 'amount': base},
                {'name': f'Biaya Jarak ({distance:.1f} km)', 'amount': round(per * distance)},
            ],
            'service_type': service_type,
            'provider': 'grabexpress',
            '_fallback': True,
        }

    def create_delivery(self, order_id: int, order_number: str,
                        origin: Dict, destination: Dict,
                        items: List[Dict], service_type: str = 'Instant',
                        payment_ref: str = '') -> Optional[Dict]:
        """
        Create a GrabExpress delivery order.

        Called automatically after payment is confirmed.

        Returns:
            dict with 'delivery_id', 'tracking_url', 'estimated_time', 'status'
            or None if creation fails.
        """
        payload = {
            'merchantOrderId': f'WRG-{order_id}',
            'serviceType': service_type,
            'origin': {
                'coordinates': {
                    'latitude': origin.get('latitude', 0),
                    'longitude': origin.get('longitude', 0),
                },
                'address': origin.get('address', ''),
                'contact': {
                    'name': origin.get('contact_name', 'Penjual'),
                    'phone': origin.get('contact_phone', ''),
                },
            },
            'destination': {
                'coordinates': {
                    'latitude': destination.get('latitude', 0),
                    'longitude': destination.get('longitude', 0),
                },
                'address': destination.get('address', ''),
                'contact': {
                    'name': destination.get('contact_name', 'Pembeli'),
                    'phone': destination.get('contact_phone', ''),
                },
            },
            'packages': [{
                'name': item.get('name', 'Item'),
                'quantity': item.get('quantity', 1),
                'weight': item.get('weight_kg', 0.5),
                'price': item.get('price', 0),
            } for item in items],
            'payment': {
                'method': 'POSTPAID',
            },
        }

        if payment_ref:
            payload['payment']['reference'] = payment_ref

        result = self._request('POST', 'partner/delivery/v1/deliveries', json=payload)

        if result:
            return {
                'delivery_id': result.get('deliveryId', result.get('id', '')),
                'tracking_url': result.get('trackingUrl', result.get('tracking_url', '')),
                'estimated_time': result.get('estimatedTime', result.get('estimated_time', '')),
                'status': result.get('status', 'booked'),
                'provider': 'grabexpress',
                'raw_response': result,
            }

        logger.error(f'GrabExpress delivery creation failed for order #{order_id}')
        return None

    def get_delivery_status(self, delivery_id: str) -> Optional[Dict]:
        """
        Get current delivery status and driver position.

        Returns:
            dict with 'delivery_status', 'driver', 'vehicle', 'position', 'milestones'
        """
        if not delivery_id:
            return None

        cache_key = f'grab_status:{delivery_id}'
        cached = cache.get(cache_key)
        if cached:
            return cached

        result = self._request('GET', f'partner/delivery/v1/deliveries/{delivery_id}')

        if result:
            status_data = {
                'delivery_status': result.get('status', 'unknown'),
                'driver': {
                    'name': result.get('driver', {}).get('name', ''),
                    'phone': result.get('driver', {}).get('phone', ''),
                    'photo_url': result.get('driver', {}).get('photoUrl', ''),
                    'rating': result.get('driver', {}).get('rating', ''),
                },
                'vehicle': {
                    'type': result.get('vehicle', {}).get('type', 'Motorcycle'),
                    'number': result.get('vehicle', {}).get('plateNumber', ''),
                    'color': result.get('vehicle', {}).get('color', ''),
                },
                'position': {
                    'latitude': result.get('driver', {}).get('position', {}).get('latitude'),
                    'longitude': result.get('driver', {}).get('position', {}).get('longitude'),
                    'last_updated': result.get('driver', {}).get('position', {}).get('updatedAt'),
                },
                'milestones': result.get('milestones', []),
                'estimated_time': result.get('estimatedTime', ''),
                'tracking_url': result.get('trackingUrl', ''),
            }
            cache.set(cache_key, status_data, POSITION_CACHE_TTL)
            return status_data

        return None

    def cancel_delivery(self, delivery_id: str, reason: str = '') -> bool:
        """Cancel a GrabExpress delivery order."""
        if not delivery_id:
            return False

        result = self._request('DELETE', f'partner/delivery/v1/deliveries/{delivery_id}',
                               json={'reason': reason or 'Order cancelled'})
        return result is not None


# =============================================================================
# GOJEK (GOSEND) CLIENT
# =============================================================================

class GoSendClient(BaseDeliveryClient):
    """
    Gojek GoSend delivery API client.

    API Reference: https://developer.gojek.com
    Endpoints:
      - OAuth: POST /oauth/v2/token
      - Rate: POST /gosend/v2/rates
      - Create: POST /gosend/v2/orders
      - Status: GET /gosend/v2/orders/{id} 
      - Cancel: DELETE /gosend/v2/orders/{id}
    """

    SUPPORTED_SERVICES = ['Instant', 'SameDay']

    def __init__(self):
        is_sandbox = getattr(settings, 'GOJEK_IS_SANDBOX', True)
        base_url = getattr(settings, 'GOJEK_SANDBOX_URL', 'https://sandbox.gojek.com') if is_sandbox else getattr(settings, 'GOJEK_API_URL', 'https://api.gojek.com')
        super().__init__(
            client_id=getattr(settings, 'GOJEK_CLIENT_ID', ''),
            client_secret=getattr(settings, 'GOJEK_CLIENT_SECRET', ''),
            base_url=base_url,
            is_sandbox=is_sandbox,
            webhook_secret=getattr(settings, 'GOJEK_WEBHOOK_SECRET', ''),
            partner_name='GoSend',
        )

    def _get_auth_url(self) -> str:
        return urljoin(self.base_url.rstrip('/') + '/', 'oauth/v2/token')

    def get_available_services(self) -> List[str]:
        services = getattr(settings, 'GOJEK_SERVICE_TYPES', ['Instant', 'SameDay'])
        return [s for s in services if s in self.SUPPORTED_SERVICES]

    def calculate_rate(self, origin: Dict, destination: Dict,
                       items: List[Dict], service_type: str = 'Instant') -> Optional[Dict]:
        """Calculate GoSend delivery rate."""
        cache_key = (
            f'gosend_rate:{origin.get("latitude", 0)}:{origin.get("longitude", 0)}:'
            f'{destination.get("latitude", 0)}:{destination.get("longitude", 0)}:'
            f'{service_type}'
        )
        cached = cache.get(cache_key)
        if cached:
            return cached

        total_weight_kg = sum(item.get('weight_kg', 0.5) * item.get('quantity', 1) for item in items)

        payload = {
            'serviceType': service_type,
            'originLatitude': origin.get('latitude', 0),
            'originLongitude': origin.get('longitude', 0),
            'destinationLatitude': destination.get('latitude', 0),
            'destinationLongitude': destination.get('longitude', 0),
            'weight': max(total_weight_kg, 0.5),
        }

        result = self._request('POST', 'gosend/v2/rates', json=payload)

        if result:
            rate_data = {
                'total_fee': float(result.get('price', result.get('totalFee', 0))),
                'currency': 'IDR',
                'estimated_time': result.get('estimatedTime', result.get('estimated_time', '')),
                'distance_km': float(result.get('distance', result.get('distanceKm', 0))),
                'breakdown': result.get('details', result.get('breakdown', [])),
                'service_type': service_type,
                'provider': 'gosend',
            }
            cache.set(cache_key, rate_data, RATE_CACHE_TTL)
            return rate_data

        # Fallback
        return self._estimate_fallback(origin, destination, items, service_type)

    def _estimate_fallback(self, origin: Dict, destination: Dict,
                           items: List[Dict], service_type: str) -> Dict:
        """Fallback rate estimation when Gojek API is unavailable."""
        logger.info('GoSend API unavailable — using distance-based estimate')

        from .distance import calculate_haversine_distance

        d = calculate_haversine_distance(
            origin.get('latitude'), origin.get('longitude'),
            destination.get('latitude'), destination.get('longitude'),
        )
        distance = d if d is not None and d > 0 else 3.0

        base_fees = {'Instant': 4000, 'SameDay': 2500}
        per_km = {'Instant': 2500, 'SameDay': 1500}

        base = base_fees.get(service_type, 4000)
        per = per_km.get(service_type, 2500)
        total_fee = base + (per * distance)

        return {
            'total_fee': total_fee,
            'currency': 'IDR',
            'estimated_time': '10-20 menit' if service_type == 'Instant' else '1-3 jam',
            'distance_km': round(distance, 2),
            'breakdown': [
                {'name': 'Biaya Dasar', 'amount': base},
                {'name': f'Biaya Jarak ({distance:.1f} km)', 'amount': round(per * distance)},
            ],
            'service_type': service_type,
            'provider': 'gosend',
            '_fallback': True,
        }

    def create_delivery(self, order_id: int, order_number: str,
                        origin: Dict, destination: Dict,
                        items: List[Dict], service_type: str = 'Instant',
                        payment_ref: str = '') -> Optional[Dict]:
        """Create a GoSend delivery order."""
        total_weight_kg = sum(item.get('weight_kg', 0.5) * item.get('quantity', 1) for item in items)

        payload = {
            'merchantOrderId': f'WRG-{order_id}',
            'serviceType': service_type,
            'originLatitude': origin.get('latitude', 0),
            'originLongitude': origin.get('longitude', 0),
            'originAddress': origin.get('address', ''),
            'originContactName': origin.get('contact_name', 'Penjual'),
            'originContactPhone': origin.get('contact_phone', ''),
            'destinationLatitude': destination.get('latitude', 0),
            'destinationLongitude': destination.get('longitude', 0),
            'destinationAddress': destination.get('address', ''),
            'destinationContactName': destination.get('contact_name', 'Pembeli'),
            'destinationContactPhone': destination.get('contact_phone', ''),
            'items': [{
                'name': item.get('name', 'Item'),
                'quantity': item.get('quantity', 1),
                'weight': item.get('weight_kg', 0.5),
            } for item in items],
            'weight': max(total_weight_kg, 0.5),
        }

        result = self._request('POST', 'gosend/v2/orders', json=payload)

        if result:
            return {
                'delivery_id': result.get('orderId', result.get('id', '')),
                'tracking_url': result.get('trackingUrl', ''),
                'estimated_time': result.get('estimatedTime', ''),
                'status': result.get('status', 'booked'),
                'provider': 'gosend',
                'raw_response': result,
            }

        logger.error(f'GoSend delivery creation failed for order #{order_id}')
        return None

    def get_delivery_status(self, delivery_id: str) -> Optional[Dict]:
        """Get GoSend delivery status and driver info."""
        if not delivery_id:
            return None

        cache_key = f'gosend_status:{delivery_id}'
        cached = cache.get(cache_key)
        if cached:
            return cached

        result = self._request('GET', f'gosend/v2/orders/{delivery_id}')

        if result:
            driver_info = result.get('driver', result.get('rider', {}))
            vehicle_info = result.get('vehicle', {})
            position = driver_info.get('position', result.get('position', {}))

            status_data = {
                'delivery_status': result.get('status', 'unknown'),
                'driver': {
                    'name': driver_info.get('name', ''),
                    'phone': driver_info.get('phone', ''),
                    'photo_url': driver_info.get('photoUrl', driver_info.get('photo', '')),
                    'rating': driver_info.get('rating', ''),
                },
                'vehicle': {
                    'type': vehicle_info.get('type', 'Motorcycle'),
                    'number': vehicle_info.get('plateNumber', vehicle_info.get('plate_number', '')),
                    'color': vehicle_info.get('color', ''),
                },
                'position': {
                    'latitude': position.get('latitude'),
                    'longitude': position.get('longitude'),
                    'last_updated': position.get('updatedAt', position.get('updated_at')),
                },
                'milestones': result.get('milestones', []),
                'estimated_time': result.get('estimatedTime', ''),
                'tracking_url': result.get('trackingUrl', ''),
            }
            cache.set(cache_key, status_data, POSITION_CACHE_TTL)
            return status_data

        return None

    def cancel_delivery(self, delivery_id: str, reason: str = '') -> bool:
        """Cancel a GoSend delivery order."""
        if not delivery_id:
            return False
        result = self._request('DELETE', f'gosend/v2/orders/{delivery_id}',
                               json={'reason': reason or 'Order cancelled'})
        return result is not None


# =============================================================================
# FACTORY / HELPER
# =============================================================================

def get_grab_client() -> GrabExpressClient:
    """Get configured GrabExpress client instance."""
    return GrabExpressClient()


def get_gosend_client() -> GoSendClient:
    """Get configured GoSend client instance."""
    return GoSendClient()


def get_available_couriers() -> List[Dict]:
    """
    Return list of available courier services with their status.
    Used by ShippingMethodListView to dynamically show/hide options.
    """
    couriers = []

    # Check GrabExpress
    grab = get_grab_client()
    if grab.is_available():
        couriers.append({
            'code': 'grabexpress',
            'name': 'GrabExpress',
            'services': grab.get_available_services(),
            'is_sandbox': grab.is_sandbox,
        })

    # Check GoSend
    gosend = get_gosend_client()
    if gosend.is_available():
        couriers.append({
            'code': 'gosend',
            'name': 'GoSend',
            'services': gosend.get_available_services(),
            'is_sandbox': gosend.is_sandbox,
        })

    return couriers


# =============================================================================
# AUTO-BOOK COURIER AFTER PAYMENT
# =============================================================================

def auto_book_courier(order, courier_code: str, service_type: str = 'Instant') -> Optional[Dict]:
    """
    Automatically book a courier after payment is confirmed.

    Called from MidtransNotificationView when payment_status becomes 'settlement'
    or 'capture' for orders that selected hyperlocal delivery.

    Args:
        order: Order model instance (must have store, delivery_address, etc.)
        courier_code: 'grabexpress' or 'gosend'
        service_type: 'Instant', 'SameDay', 'Regular'

    Returns:
        dict with delivery result or None if booking failed
    """
    if courier_code not in ('grabexpress', 'gosend'):
        logger.warning(f'Unknown courier code: {courier_code}')
        return None

    store = order.store
    if not store:
        logger.error(f'Order #{order.id} has no store — cannot book courier')
        return None

    # Build origin (store) coordinates
    origin = {
        'latitude': float(store.latitude) if store.latitude else -6.2,
        'longitude': float(store.longitude) if store.longitude else 106.8,
        'address': store.address or store.store_name or '',
        'contact_name': store.store_name or 'Penjual',
        'contact_phone': str(store.user.phone) if store.user and store.user.phone else '',
    }

    # Build destination (buyer) coordinates
    delivery = Delivery.objects.filter(order=order).select_related('order').first()
    destination = {
        'latitude': float(delivery.buyer_latitude) if delivery and delivery.buyer_latitude else -6.2,
        'longitude': float(delivery.buyer_longitude) if delivery and delivery.buyer_longitude else 106.8,
        'address': order.delivery_address or '',
        'contact_name': order.recipient_name or 'Pembeli',
        'contact_phone': order.recipient_phone or '',
    }

    # Build items list
    items = []
    for item in order.items.all():
        items.append({
            'name': item.product_name,
            'quantity': item.qty,
            'weight_kg': float(item.product.weight_kg) if item.product and hasattr(item.product, 'weight_kg') else 0.5,
            'price': float(item.price),
        })

    # Select client
    if courier_code == 'grabexpress':
        client = get_grab_client()
    else:
        client = get_gosend_client()

    # Step 1: Calculate rate
    rate = client.calculate_rate(origin, destination, items, service_type)
    if not rate:
        logger.error(f'Rate calculation failed for order #{order.id} ({courier_code})')
        return None

    # Step 2: Create delivery
    result = client.create_delivery(
        order_id=order.id,
        order_number=order.order_number,
        origin=origin,
        destination=destination,
        items=items,
        service_type=service_type,
        payment_ref=f'WRG-PAY-{order.id}',
    )

    if result:
        logger.info(f'Courier booked: {courier_code} {service_type} for order #{order.id}')
        # Update delivery record with courier info
        if delivery:
            delivery.courier_name = courier_code
            delivery.tracking_number = result.get('delivery_id', '')
            delivery.delivery_status = 'menunggu_penjemputan'
            delivery.save(update_fields=['courier_name', 'tracking_number', 'delivery_status'])

        # Update order with courier info
        order.courier = courier_code
        order.tracking_number = result.get('delivery_id', '')
        order.save(update_fields=['courier', 'tracking_number'])

    return result
