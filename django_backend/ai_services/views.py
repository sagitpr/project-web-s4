"""
AI Services API Views.
Exposes all AI-powered features through REST API endpoints.
"""

import json
import logging
import uuid
from rest_framework import status, permissions, views, generics, serializers
from rest_framework.response import Response
from django.conf import settings
from django.core.cache import cache

from .gemini_client import get_gemini_client
from .recommendation import get_recommendation_engine
from .search import get_smart_search
from .vision import get_vision_service
from .product_description import get_description_generator
from .review_analyzer import get_review_analyzer
from .seller_assistant import get_seller_assistant
from .category_classifier import get_category_classifier
from .fraud_detection import get_fraud_detection
from .notification_generator import get_notification_generator
from .dashboard_insights import get_dashboard_insights
from drf_spectacular.utils import extend_schema
from notifications.services import notify_ai_scan_complete

# Celery task imports — wrapped so import doesn't fail if Celery/Redis is down
try:
    from .tasks import analyze_vision_task
except ImportError:
    analyze_vision_task = None

logger = logging.getLogger('django_backend.ai_services.views')


# ── AI Health / Connection Verification ──

@extend_schema(exclude=True)
class AIHealthView(views.APIView):
    """Verify AI service connection and API key validity."""
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        client = get_gemini_client()
        if not client.api_key:
            return Response({
                'status': 'unconfigured',
                'message': 'Gemini API key not configured. Set GEMINI_KEY or VERTEX_KEY in .env',
                'gemini_key_set': False,
                'gcp_project_set': bool(settings.GCP_PROJECT_ID),
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        # Quick connectivity test
        try:
            result = client.generate_text(
                prompt='Respond with: OK',
                max_output_tokens=10,
                temperature=0.0,
            )
            if result and 'OK' in result:
                return Response({
                    'status': 'connected',
                    'message': 'Gemini API connection verified',
                    'gemini_key_set': True,
                    'test_response': result.strip(),
                })
        except Exception as e:
            logger.error("Gemini health check failed: %s", e)

        return Response({
            'status': 'error',
            'message': 'Gemini API connection failed. Check API key validity.',
            'gemini_key_set': True,
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


# ── Product Recommendations ──

@extend_schema(exclude=True)
class AIRecommendationsView(views.APIView):
    """Get AI-powered personalized product recommendations."""
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        engine = get_recommendation_engine(request.user)
        limit = int(request.GET.get('limit', 20))
        include_ai = request.GET.get('ai_explanation', 'true').lower() == 'true'

        recommendations = engine.get_personalized_recommendations(
            limit=limit,
            include_ai_explanation=include_ai,
        )
        return Response(recommendations)


@extend_schema(exclude=True)
class AISimilarProductsView(views.APIView):
    """Get AI-powered similar product recommendations."""
    permission_classes = (permissions.AllowAny,)

    def get(self, request, product_id):
        limit = int(request.GET.get('limit', 8))
        engine = get_recommendation_engine(request.user if request.user.is_authenticated else None)
        similar = engine.get_similar_products(product_id, limit=limit)
        return Response({'results': similar, 'total': len(similar)})


# ── Smart Search ──

@extend_schema(exclude=True)
class AISmartSearchView(views.APIView):
    """AI-powered smart product search with natural language understanding."""
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        query = request.GET.get('q', '').strip()
        if not query:
            return Response({'results': [], 'total': 0, 'query': query})

        limit = int(request.GET.get('limit', 20))
        searcher = get_smart_search()
        results = searcher.search(query, limit=limit)
        return Response(results)


@extend_schema(exclude=True)
class AISearchSuggestionsView(views.APIView):
    """Get real-time search suggestions."""
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        query = request.GET.get('q', '').strip()
        if not query or len(query) < 2:
            return Response({'suggestions': []})

        searcher = get_smart_search()
        suggestions = searcher.get_suggestions(query)
        return Response({'suggestions': suggestions})


# ── Vision Analysis ──

@extend_schema(exclude=True)
class AIProductVisionView(views.APIView):
    """Analyze product images with AI (freshness, OCR, quality).
    
    Supports both synchronous and asynchronous modes.
    - Default (async): returns task_id immediately, process in background
    - sync=true: returns result directly (may block 3-10s)
    """
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        image_data = request.data.get('image', '')
        product_name = request.data.get('product_name', '')
        analysis_type = request.data.get('analysis_type', 'full')
        sync_mode = request.data.get('sync', '').lower() == 'true'

        if not image_data:
            return Response({'error': 'Image data is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if sync_mode:
            # Synchronous mode (legacy) — blocks until Gemini responds
            vision = get_vision_service()
            if analysis_type == 'freshness':
                result = vision.analyze_freshness(image_data, product_name)
            elif analysis_type == 'label':
                result = vision.scan_label(image_data)
            else:
                result = vision.analyze_product_image(image_data, product_name)
            # Notify on sync completion
            try:
                if result and result.get('status') in ('success', None):
                    pname = product_name or result.get('title', 'Produk')
                    confidence = float(result.get('confidence', 0) or 0)
                    notify_ai_scan_complete(request.user.id, pname, result, confidence)
            except Exception as exc:
                logger.warning('AI scan notification failed: %s', exc)
            return Response(result)

        # Async mode (default) — dispatch to Celery, return task_id
        task_id = str(uuid.uuid4())

        # Validate image data size before dispatching
        if len(image_data) > 10 * 1024 * 1024:  # 10MB limit for base64
            return Response({'error': 'Image terlalu besar. Maksimal 10MB.'}, 
                          status=status.HTTP_400_BAD_REQUEST)

        # Cache pending status immediately
        cache.set(f'vision_task_{task_id}', {
            'status': 'pending',
            'result': None,
            'error': None,
        }, 300)  # 5 min TTL

        # Dispatch to Celery worker
        try:
            analyze_vision_task.delay(
                task_id=task_id,
                image_data=image_data,
                product_name=product_name,
                analysis_type=analysis_type,
            )
        except Exception as e:
            logger.error('Failed to dispatch vision task: %s', e)
            # Fall back to sync if Celery is unavailable
            vision = get_vision_service()
            if analysis_type == 'freshness':
                result = vision.analyze_freshness(image_data, product_name)
            elif analysis_type == 'label':
                result = vision.scan_label(image_data)
            else:
                result = vision.analyze_product_image(image_data, product_name)
            return Response(result)

        return Response({
            'task_id': task_id,
            'status': 'pending',
            'message': 'Analisis sedang diproses. Gunakan task_id untuk mengambil hasil.',
        })


@extend_schema(exclude=True)
class AIVisionTaskStatusView(views.APIView):
    """Get the status/result of an async vision analysis task."""
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, task_id):
        cached = cache.get(f'vision_task_{task_id}')
        if not cached:
            return Response({
                'status': 'not_found',
                'error': 'Task ID tidak ditemukan atau sudah kedaluwarsa.',
            }, status=status.HTTP_404_NOT_FOUND)

        response = {
            'status': cached['status'],
        }
        if cached['status'] == 'completed':
            response['result'] = cached['result']
        elif cached['status'] == 'failed':
            response['error'] = cached.get('error', 'Unknown error')

        return Response(response)


@extend_schema(exclude=True)
class AIFreshnessDetectionView(views.APIView):
    """AI-powered freshness detection for produce.
    
    Supports synchronous and asynchronous modes.
    """
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        image_data = request.data.get('image', '')
        product_name = request.data.get('product_name', '')
        sync_mode = request.data.get('sync', '').lower() == 'true'

        if not image_data:
            return Response({'error': 'Image data is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if sync_mode:
            vision = get_vision_service()
            result = vision.analyze_freshness(image_data, product_name)
            return Response(result)

        # Async mode — dispatch to Celery
        task_id = str(uuid.uuid4())
        cache.set(f'vision_task_{task_id}', {
            'status': 'pending',
            'result': None,
            'error': None,
        }, 300)

        try:
            analyze_vision_task.delay(
                task_id=task_id,
                image_data=image_data,
                product_name=product_name,
                analysis_type='freshness',
            )
        except Exception as e:
            logger.error('Failed to dispatch freshness task: %s', e)
            vision = get_vision_service()
            result = vision.analyze_freshness(image_data, product_name)
            return Response(result)

        return Response({
            'task_id': task_id,
            'status': 'pending',
            'message': 'Analisis kesegaran sedang diproses.',
        })


# ── Product Description Generator ──

@extend_schema(exclude=True)
class AIProductDescriptionView(views.APIView):
    """Generate AI product descriptions."""
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        product_name = request.data.get('product_name', '')
        if not product_name:
            return Response({'error': 'product_name is required.'}, status=status.HTTP_400_BAD_REQUEST)

        generator = get_description_generator()
        result = generator.generate_description(
            product_name=product_name,
            category_name=request.data.get('category_name', ''),
            price=request.data.get('price'),
            unit=request.data.get('unit', ''),
            additional_info=request.data.get('additional_info', ''),
            image_data=request.data.get('image'),
        )
        return Response(result)


# ── Review Analyzer ──

@extend_schema(exclude=True)
class AIReviewAnalysisView(views.APIView):
    """Analyze product reviews with AI sentiment analysis."""
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        product_id = request.GET.get('product_id')
        store_id = request.GET.get('store_id')

        if not product_id and not store_id:
            return Response({'error': 'Provide product_id or store_id'}, status=status.HTTP_400_BAD_REQUEST)

        analyzer = get_review_analyzer()
        result = analyzer.analyze_reviews(
            product_id=int(product_id) if product_id else None,
            store_id=int(store_id) if store_id else None,
        )
        return Response(result)


# ── Seller Assistant ──

@extend_schema(exclude=True)
class AISellerAssistantView(views.APIView):
    """AI business insights and recommendations for sellers."""
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        user = request.user
        if user.role != 'seller':
            return Response({'error': 'Only sellers can access this endpoint.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            store = user.store
        except AttributeError:
            return Response({'error': 'No store found for this seller.'}, status=status.HTTP_404_NOT_FOUND)

        days = int(request.GET.get('days', 30))
        assistant = get_seller_assistant(store)
        result = assistant.get_comprehensive_analysis(days=days)
        return Response(result)


@extend_schema(exclude=True)
class AISellerStockView(views.APIView):
    """AI stock recommendations for sellers."""
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        user = request.user
        if user.role != 'seller':
            return Response({'error': 'Only sellers can access this endpoint.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            store = user.store
        except AttributeError:
            return Response({'error': 'No store found.'}, status=status.HTTP_404_NOT_FOUND)

        assistant = get_seller_assistant(store)
        stock_recs = assistant.get_stock_recommendations()
        promo_recs = assistant.get_promotion_recommendations()
        
        # Send notification for stock recommendations
        try:
            from notifications.services import notify_stock_prediction
            for rec in (stock_recs or []):
                product_name = rec.get('product_name', 'Produk')
                predicted_days = rec.get('predicted_days', 7)
                current_stock = rec.get('current_stock', 0)
                notify_stock_prediction(request.user.id, product_name, predicted_days, current_stock)
        except Exception as exc:
            logger.warning('Stock prediction notification failed: %s', exc)
        
        return Response({'stock_recommendations': stock_recs, 'promotion_recommendations': promo_recs})


# ── Category Classification ──

@extend_schema(exclude=True)
class AICategoryClassifierView(views.APIView):
    """AI-powered product category classification."""
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        product_name = request.data.get('product_name', '')
        if not product_name:
            return Response({'error': 'product_name is required.'}, status=status.HTTP_400_BAD_REQUEST)

        classifier = get_category_classifier()
        result = classifier.classify(
            product_name=product_name,
            description=request.data.get('description', ''),
            image_data=request.data.get('image'),
        )
        return Response(result)


# ── Fraud Detection ──

@extend_schema(exclude=True)
class AIFraudOrderView(views.APIView):
    """AI fraud detection for a specific order."""
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, order_id):
        from orders.models import Order
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

        detector = get_fraud_detection()
        result = detector.analyze_order(order)
        return Response(result)


@extend_schema(exclude=True)
class AIFraudUserView(views.APIView):
    """AI fraud analysis for a user account."""
    permission_classes = (permissions.IsAdminUser,)

    def get(self, request, user_id):
        try:
            from accounts.models import User
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        detector = get_fraud_detection()
        result = detector.analyze_user(user)
        return Response(result)


# ── Notification Generator ──

@extend_schema(exclude=True)
class AINotificationGenerateView(views.APIView):
    """Generate AI-powered personalized notifications."""
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        notif_type = request.data.get('type', 'promo')
        generator = get_notification_generator()

        if notif_type == 'birthday':
            result = generator.generate_birthday_promo(request.user)
        elif notif_type == 'promo':
            from stores.models import Store
            store = getattr(request.user, 'store', None)
            result = generator.generate_personalized_promo(request.user, store=store)
        else:
            result = generator.generate_personalized_promo(request.user)

        if not result:
            return Response({'error': 'Failed to generate notification.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(result)


# ── Dashboard Insights ──

@extend_schema(exclude=True)
class AIDashboardSellerView(views.APIView):
    """AI-generated dashboard insights for sellers."""
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        user = request.user
        if user.role != 'seller':
            return Response({'error': 'Seller access required.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            store = user.store
        except AttributeError:
            return Response({'error': 'No store found.'}, status=status.HTTP_404_NOT_FOUND)

        days = int(request.GET.get('days', 30))
        insights = get_dashboard_insights()
        result = insights.seller_dashboard_insights(store, days=days)
        return Response(result)


@extend_schema(exclude=True)
class AIDashboardAdminView(views.APIView):
    """AI-generated platform insights for administrators."""
    permission_classes = (permissions.IsAdminUser,)

    def get(self, request):
        days = int(request.GET.get('days', 30))
        insights = get_dashboard_insights()
        result = insights.admin_dashboard_insights(days=days)
        return Response(result)
