"""
Celery tasks for AI Services — async vision analysis and AI processing.
Moves Gemini Vision API calls (3-10s) out of the request thread.
"""

import logging
from celery import shared_task
from django.core.cache import cache

logger = logging.getLogger('django_backend.ai_services.tasks')

VISION_RESULT_CACHE_TTL = 300  # 5 minutes

@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def analyze_vision_task(self, task_id: str, image_data: str, product_name: str = '',
                         analysis_type: str = 'full') -> dict:
    """
    Process AI vision analysis asynchronously.
    
    Calls Gemini Vision API (blocking 3-10s) without holding the web worker.
    Results are cached by task_id so the frontend can poll for them.
    
    Args:
        task_id: Unique identifier for this task (used as cache key)
        image_data: Base64-encoded image data
        product_name: Optional product name for context
        analysis_type: 'full', 'freshness', or 'label'
    
    Returns:
        dict: Vision analysis result
    """
    logger.info('Vision task %s started (type=%s, product=%s)', 
                task_id, analysis_type, product_name or 'unknown')

    try:
        from .vision import get_vision_service
        vision = get_vision_service()

        if analysis_type == 'freshness':
            result = vision.analyze_freshness(image_data, product_name)
        elif analysis_type == 'label':
            result = vision.scan_label(image_data)
        else:
            result = vision.analyze_product_image(image_data, product_name)

        # Mark as complete
        result['task_id'] = task_id
        result['task_status'] = 'completed'
        result['task_completed_at'] = __import__('datetime').datetime.now().isoformat()

        # Cache result
        cache.set(f'vision_task_{task_id}', {
            'status': 'completed',
            'result': result,
            'error': None,
        }, VISION_RESULT_CACHE_TTL)

        logger.info('Vision task %s completed successfully', task_id)
        return result

    except Exception as exc:
        logger.error('Vision task %s failed: %s', task_id, str(exc))
        error_result = {
            'status': 'error',
            'error': str(exc),
            'task_status': 'failed',
            'task_id': task_id,
        }
        cache.set(f'vision_task_{task_id}', {
            'status': 'failed',
            'result': None,
            'error': str(exc),
        }, VISION_RESULT_CACHE_TTL)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def generate_batch_ai_insights_task(self, store_id: int, days: int = 30) -> dict:
    """
    Generate AI insights for a seller dashboard asynchronously.
    Runs CPU-heavy analytics + Gemini calls without blocking.
    """
    logger.info('Batch AI insights task started for store %s (days=%d)', store_id, days)
    try:
        from .seller_assistant import get_seller_assistant
        from stores.models import Store
        store = Store.objects.get(id=store_id)
        assistant = get_seller_assistant(store)
        result = assistant.get_comprehensive_analysis(days=days)
        return result
    except Exception as exc:
        logger.exception('Batch AI insights failed for store %s: %s', store_id, exc)
        return {'error': str(exc), 'store_id': store_id}
