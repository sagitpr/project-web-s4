"""
Celery tasks for AI Intelligence Platform.
Digital Twin updates, health monitoring, predictions, segmentation, gamification.
"""

import logging
from celery import shared_task
from django.db import connection
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


@shared_task
def update_digital_twin_task(user_id: int):
    """Update a single user's digital twin."""
    from django.contrib.auth import get_user_model
    from ai_intelligence.services.digital_twin import get_digital_twin_engine
    User = get_user_model()
    connection.close_if_unusable_or_obsolete()
    try:
        user = User.objects.get(id=user_id)
        engine = get_digital_twin_engine()
        engine.update_digital_twin(user)
    except User.DoesNotExist:
        logger.warning('User %s not found for digital twin', user_id)


@shared_task
def batch_update_digital_twins_task(batch_size: int = 50):
    """Batch update digital twins for all users."""
    from django.contrib.auth import get_user_model
    from ai_intelligence.models import DigitalTwin
    User = get_user_model()
    users = User.objects.filter(is_active=True).order_by('?')[:batch_size]
    count = 0
    for user in users:
        update_digital_twin_task.delay(user.id)
        count += 1
    logger.info('Dispatched %d digital twin updates', count)
    return {'dispatched': count}


@shared_task
def update_gamification_task(user_id: int, event_type: str = ''):
    """Update gamification profile after a user action."""
    from django.contrib.auth import get_user_model
    from ai_intelligence.services.gamification import get_gamification_engine
    User = get_user_model()
    connection.close_if_unusable_or_obsolete()
    try:
        user = User.objects.get(id=user_id)
        engine = get_gamification_engine()
        engine.update_gamification(user, event_type)
        engine.update_challenge_progress(user, event_type)
    except User.DoesNotExist:
        logger.warning('User %s not found for gamification', user_id)


@shared_task
def capture_marketplace_health_task():
    """Capture a marketplace health snapshot."""
    from ai_intelligence.services.marketplace_health import get_marketplace_health_service
    service = get_marketplace_health_service()
    snapshot = service.capture_snapshot()
    logger.info('Marketplace health captured: score=%.1f', snapshot.marketplace_health_score)
    return {'health_score': snapshot.marketplace_health_score}


@shared_task
def segment_all_users_task(batch_size: int = 100):
    """Run customer segmentation for all active users."""
    from django.contrib.auth import get_user_model
    from ai_intelligence.models import CustomerSegment, UserSegmentAssignment
    from ai_intelligence.services.segmentation import get_segmentation_engine
    User = get_user_model()
    engine = get_segmentation_engine()

    for user in User.objects.filter(is_active=True)[:batch_size]:
        segment_name = engine.segment_user(user)
        segment, _ = CustomerSegment.objects.get_or_create(
            name=segment_name, segment_type='rfm',
            defaults={'description': engine.get_segment_characteristics(segment_name)['description']}
        )
        UserSegmentAssignment.objects.update_or_create(
            user=user, segment=segment,
            defaults={'score': 1.0, 'is_primary': True}
        )
    logger.info('Segmented %d users', min(batch_size, User.objects.count()))
    return {'segmented': min(batch_size, User.objects.count())}


@shared_task
def generate_coach_insights_task(batch_size: int = 20):
    """Generate business coach insights for active sellers."""
    from stores.models import Store
    from ai_intelligence.models import BusinessCoachInsight
    from ai_intelligence.services.business_coach import get_business_coach_service

    stores = Store.objects.filter(is_active=True)[:batch_size]
    coach = get_business_coach_service()
    count = 0
    for store in stores:
        try:
            insights = coach.generate_insights_for_store(store)
            for insight in insights:
                BusinessCoachInsight.objects.create(
                    store=store,
                    computed_at=timezone.now(),
                    **insight
                )
            count += len(insights)
        except Exception as e:
            logger.warning('Coach insights failed for store %s: %s', store.id, e)
    logger.info('Generated %d coach insights', count)
    return {'insights': count}


@shared_task
def predict_demand_task(product_id: int):
    """Predict demand for a product."""
    from products.models import Product
    from ai_intelligence.models import DemandPrediction
    from ai_intelligence.services.prediction_engine import get_prediction_engine
    connection.close_if_unusable_or_obsolete()
    try:
        product = Product.objects.get(id=product_id)
        engine = get_prediction_engine()
        result = engine.predict_demand(product)
        DemandPrediction.objects.create(
            product=product,
            store=product.store,
            forecast_date=timezone.now().date() + timedelta(days=7),
            forecast_period='weekly',
            model_version='v1',
            computed_at=timezone.now(),
            **result
        )
    except Product.DoesNotExist:
        logger.warning('Product %s not found', product_id)


@shared_task
def clean_old_predictions_task():
    """Clean old predictions and snapshots."""
    from ai_intelligence.models import DemandPrediction, SalesForecast, MarketplaceHealthSnapshot
    cutoff = timezone.now() - timedelta(days=90)
    DemandPrediction.objects.filter(computed_at__lt=cutoff).delete()
    SalesForecast.objects.filter(computed_at__lt=cutoff).delete()
    MarketplaceHealthSnapshot.objects.filter(snapshot_time__lt=cutoff).delete()
    logger.info('Cleaned old predictions and snapshots')
