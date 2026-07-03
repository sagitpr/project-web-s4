"""
Celery tasks for products — async Smart Scan AI and Stock Prediction.
Moves Gemini Vision API calls (3-10s) and CPU-heavy predictions out of request thread.
"""

import logging
from celery import shared_task
from django.core.cache import cache

logger = logging.getLogger(__name__)

# ── Cache TTLs ──
PREDICTION_CACHE_TTL = 60 * 15  # 15 minutes
REORDER_CACHE_TTL = 60 * 10     # 10 minutes


@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def process_smart_scan_task(self, product_id, scan_type='computer_vision', options=None):
    """
    Process Smart Scan AI analysis asynchronously.
    Calls Gemini Vision API (blocking 3-10s) without holding the web worker.
    
    Returns quality analysis result structured for frontend.
    """
    import json
    from products.models import Product, QualityCheck
    from products.services.smart_scan import process_scan

    options = options or {}

    try:
        product = Product.objects.select_related('category').get(id=product_id)
    except Product.DoesNotExist:
        logger.error('smart_scan_task: Product %s not found', product_id)
        return {'error': 'Produk tidak ditemukan.', 'product_id': product_id}

    try:
        # Process scan — this is the heavy call (Gemini API)
        result = process_scan(product, scan_type, options)
    except Exception as exc:
        logger.error('smart_scan_task error for product %s: %s', product_id, str(exc))
        raise self.retry(exc=exc)

    quality_status = result.get('quality_status', 'pending')
    freshness_score = result.get('freshness_score', 0)
    ai_result = result.get('ai_result', '')

    # Persist QualityCheck record
    if quality_status != 'pending' or scan_type in ('barcode', 'manual'):
        from django.db import transaction
        with transaction.atomic():
            qc = QualityCheck.objects.create(
                product=product,
                freshness_score=freshness_score,
                quality_status=quality_status,
                stock_status='sufficient',
                ai_result=ai_result,
            )
            if quality_status in ('fresh', 'normal', 'warning', 'rejected'):
                product.quality_score = freshness_score
                product.save(update_fields=['quality_score'])
            result['quality_check_id'] = qc.id

    result['product'] = {
        'id': product.id,
        'product_name': product.product_name,
        'product_photo': product.product_photo.url if product.product_photo else None,
    }
    result['eligible_for_sale'] = quality_status not in ('rejected', 'pending')

    return result


@shared_task(bind=True)
def run_stock_prediction_task(self, store_id, product_id=None, days_ahead=30, history_days=90):
    """
    Run stock prediction asynchronously (CPU-heavy).
    Caches result for 15 minutes.
    
    Predicts demand for one product or all products in a store.
    """
    from products.services.stock_prediction import StockPredictor
    from products.models import Product
    from stores.models import Store

    try:
        store = Store.objects.get(id=store_id)
    except Store.DoesNotExist:
        return {'error': 'Store not found', 'store_id': store_id}

    # Cache key
    if product_id:
        cache_key = f'stock_prediction_{store_id}_{product_id}_{days_ahead}'
    else:
        cache_key = f'stock_prediction_all_{store_id}_{days_ahead}'

    # Check cache first
    cached = cache.get(cache_key)
    if cached:
        logger.info('Stock prediction cache hit for store %s', store_id)
        return cached

    try:
        predictor = StockPredictor(store=store)

        if product_id:
            product = Product.objects.filter(id=product_id, store=store).first()
            if not product:
                return {'error': 'Produk tidak ditemukan', 'product_id': product_id}
            result = predictor.predict_demand(product, days_ahead, history_days)
        else:
            result = predictor.predict_store_stock(store, days_ahead)

        # Cache result
        cache.set(cache_key, result, PREDICTION_CACHE_TTL)
        return result

    except Exception as exc:
        logger.exception('Stock prediction error for store %s', store_id)
        return {'error': str(exc), 'store_id': store_id}


@shared_task(bind=True)
def run_reorder_suggestions_task(self, store_id):
    """
    Generate reorder suggestions asynchronously.
    Uses EOQ (Economic Order Quantity) calculations (CPU-heavy).
    """
    from products.services.stock_prediction import ReorderOptimizer
    from stores.models import Store

    cache_key = f'reorder_suggestions_{store_id}'
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        store = Store.objects.get(id=store_id)
        optimizer = ReorderOptimizer(store)
        suggestions = optimizer.get_reorder_suggestions()
        cache.set(cache_key, suggestions, REORDER_CACHE_TTL)
        return suggestions
    except Exception as exc:
        logger.exception('Reorder suggestion error for store %s', store_id)
        return {'error': str(exc), 'store_id': store_id}
