"""
Distance calculation service using the Haversine formula.
Supports hyperlocal shipping cost estimation based on coordinates.
"""

import math
from decimal import Decimal


def calculate_haversine_distance(lat1, lon1, lat2, lon2) -> float:
    """
    Calculate the great-circle distance between two points on the Earth's surface
    (specified in decimal degrees) in kilometers.
    
    Returns:
        float | None: Distance in km, or None if coordinates are missing.
    """
    if None in (lat1, lon1, lat2, lon2):
        return None
        
    try:
        # Convert decimal degrees to radians
        lat1_rad = math.radians(float(lat1))
        lon1_rad = math.radians(float(lon1))
        lat2_rad = math.radians(float(lat2))
        lon2_rad = math.radians(float(lon2))
        
        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Radius of Earth in kilometers
        r = 6371.0
        return round(c * r, 2)
        
    except (ValueError, TypeError) as e:
        import logging
        logger = logging.getLogger('django_backend')
        logger.error(f"Error calculating Haversine distance: {str(e)}")
        return None


def estimate_shipping_fee(base_fee: Decimal, distance_km: float) -> Decimal:
    """
    Estimate delivery fee based on distance.
    Rp 2,500 per km after the first 2 km.
    """
    if distance_km is None:
        return base_fee
        
    try:
        base = Decimal(str(base_fee))
        dist = Decimal(str(distance_km))
        
        included_km = Decimal('2.0')
        price_per_km = Decimal('2500.00')
        
        if dist <= included_km:
            return base
            
        extra_dist = dist - included_km
        extra_fee = extra_dist * price_per_km
        return base + extra_fee
        
    except (ValueError, TypeError):
        return base
