"""
Support / Help Center views for Warungio Marketplace API.
"""

from django.db import transaction
from django.db.models import Q
from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from .models import (
    HelpCategory, HelpArticle, FAQ, BannerPromo,
    ContactInfo, SupportInfo, ChatQuickReply, SupportTicket
)
from drf_spectacular.utils import extend_schema
from .serializers import (
    HelpCategorySerializer, HelpArticleListSerializer, HelpArticleDetailSerializer,
    FAQSerializer, BannerPromoSerializer, ContactInfoSerializer,
    SupportInfoSerializer, ChatQuickReplySerializer, SupportTicketSerializer
)


class HelpCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for help categories."""
    queryset = HelpCategory.objects.filter(is_active=True)
    serializer_class = HelpCategorySerializer
    lookup_field = 'slug'


class HelpArticleViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for help articles."""
    serializer_class = HelpArticleListSerializer
    lookup_field = 'slug'

    def get_queryset(self):
        qs = HelpArticle.objects.filter(is_published=True)
        category_slug = self.request.query_params.get('category')
        search = self.request.query_params.get('search')
        featured = self.request.query_params.get('featured')

        if category_slug:
            qs = qs.filter(category__slug=category_slug)
        if search:
            qs = qs.filter(
                Q(title__icontains=search) |
                Q(content__icontains=search) |
                Q(tags__icontains=search)
            )
        if featured:
            qs = qs.filter(is_featured=True)

        return qs

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return HelpArticleDetailSerializer
        return HelpArticleListSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Increment view count
        instance.increment_views()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def mark_helpful(self, request, slug=None):
        """Mark article as helpful."""
        article = self.get_object()
        article.helpful_count += 1
        article.save(update_fields=['helpful_count'])
        return Response({'status': 'ok', 'helpful_count': article.helpful_count})

    @action(detail=True, methods=['post'])
    def mark_not_helpful(self, request, slug=None):
        """Mark article as not helpful."""
        article = self.get_object()
        article.not_helpful_count += 1
        article.save(update_fields=['not_helpful_count'])
        return Response({'status': 'ok', 'not_helpful_count': article.not_helpful_count})


class FAQViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for FAQs."""
    queryset = FAQ.objects.filter(is_published=True)
    serializer_class = FAQSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        category_slug = self.request.query_params.get('category')
        search = self.request.query_params.get('search')
        if category_slug:
            qs = qs.filter(category__slug=category_slug)
        if search:
            qs = qs.filter(
                Q(question__icontains=search) |
                Q(answer__icontains=search)
            )
        return qs


class BannerPromoViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for active promotional banners."""
    serializer_class = BannerPromoSerializer

    def get_queryset(self):
        now = timezone.now()
        qs = BannerPromo.objects.filter(is_active=True)
        qs = qs.filter(
            Q(start_date__isnull=True) | Q(start_date__lte=now)
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=now)
        )
        position = self.request.query_params.get('position')
        if position:
            qs = qs.filter(position=position)
        return qs


class ContactInfoViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for contact information."""
    queryset = ContactInfo.objects.filter(is_active=True)
    serializer_class = ContactInfoSerializer


class SupportInfoViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for support info cards."""
    queryset = SupportInfo.objects.filter(is_active=True)
    serializer_class = SupportInfoSerializer


class ChatQuickReplyViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for chat quick reply templates."""
    queryset = ChatQuickReply.objects.filter(is_active=True)
    serializer_class = ChatQuickReplySerializer

    def get_queryset(self):
        qs = super().get_queryset()
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)
        return qs


class SupportTicketUserView(generics.ListCreateAPIView):
    """List and create support tickets for the current user."""
    serializer_class = SupportTicketSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return SupportTicket.objects.none()

        qs = SupportTicket.objects.filter(user=self.request.user)
        status = self.request.query_params.get('status')
        if status:
            qs = qs.filter(support_status=status)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SupportTicketAdminView(generics.ListAPIView):
    """List all support tickets (admin only)."""
    serializer_class = SupportTicketSerializer
    permission_classes = (permissions.IsAdminUser,)

    def get_queryset(self):
        qs = SupportTicket.objects.all()
        status = self.request.query_params.get('status')
        priority = self.request.query_params.get('priority')
        if status:
            qs = qs.filter(support_status=status)
        if priority:
            qs = qs.filter(priority=priority)
        return qs


class SupportTicketDetailView(generics.RetrieveUpdateAPIView):
    """Retrieve or update a support ticket."""
    serializer_class = SupportTicketSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        # Users can only edit their own tickets; admins can edit all
        if self.request.user.is_staff:
            return SupportTicket.objects.all()
        return SupportTicket.objects.filter(user=self.request.user)


class HelpSearchView(generics.ListAPIView):
    """Combined search across articles and FAQs."""
    serializer_class = HelpArticleListSerializer

    def get_queryset(self):
        query = self.request.query_params.get('q', '')
        if not query:
            return HelpArticle.objects.none()

        return HelpArticle.objects.filter(
            is_published=True
        ).filter(
            Q(title__icontains=query) |
            Q(content__icontains=query) |
            Q(tags__icontains=query)
        ).order_by('-views_count')[:10]

    def list(self, request, *args, **kwargs):
        articles = self.get_queryset()
        article_serializer = self.get_serializer(articles, many=True)

        # Also search FAQs (only if query is provided)
        query = request.query_params.get('q', '')
        faqs = []
        faq_serializer_data = []
        if query:
            faqs = FAQ.objects.filter(
                is_published=True
            ).filter(
                Q(question__icontains=query) |
                Q(answer__icontains=query)
            )[:5]
            faq_serializer = FAQSerializer(faqs, many=True)
            faq_serializer_data = faq_serializer.data

        return Response({
            'articles': article_serializer.data,
            'faqs': faq_serializer_data,
        })


@extend_schema(exclude=True)
class AIChatView(generics.GenericAPIView):
    """
    AI-powered customer service chat endpoint.
    
    POST: Send a message to AI and get an automated response.
    If confidence is low or escalation is triggered,
    the message will be escalated to human admin.
    """
    permission_classes = (permissions.AllowAny,)

    @transaction.atomic
    def post(self, request):
        from .ai_chat_service import get_ai_chat_service
        
        query = request.data.get('message', '').strip()
        customer_id = request.user.id if request.user.is_authenticated else None
        stream = request.data.get('stream', False)
        
        if not query:
            return Response(
                {'error': 'Pesan tidak boleh kosong.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if AI chat is enabled
        from django.conf import settings
        if not settings.AI_CHAT_ENABLED:
            return Response(
                {'error': 'AI chat service is currently unavailable.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        try:
            ai_service = get_ai_chat_service()
            
            # Generate AI response
            response_text, confidence, should_escalate = ai_service.generate_response(
                query=query,
                customer_id=customer_id,
                stream=stream
            )
            
            # Prepare response
            response_data = {
                'response': response_text,
                'confidence': round(confidence, 2),
                'escalated': should_escalate,
            }
            
            # If confidence is low or should escalate, mark for human review
            if should_escalate:
                response_data['message'] = (
                    'Tim support kami akan segera menghubungi Anda untuk bantuan lebih lanjut.'
                )
                # Create support ticket for human follow-up
                if customer_id:
                    SupportTicket.objects.create(
                        user_id=customer_id,
                        title=f'AI Escalation: {query[:50]}',
                        description=response_text,
                        priority='high' if confidence < 0.5 else 'medium',
                        support_status='pending',
                        category='ai_escalation'
                    )
            
            return Response(response_data)
        
        except Exception as e:
            import logging
            logger = logging.getLogger('django_backend')
            logger.error(f"Error in AI chat: {str(e)}")
            
            return Response(
                {
                    'error': 'Terjadi kesalahan pada service AI. Tim support kami akan menghubungi Anda segera.',
                    'escalated': True
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
