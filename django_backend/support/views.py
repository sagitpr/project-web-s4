"""
Support / Help Center views for Warungio Marketplace API.
"""

from django.contrib.auth import get_user_model
User = get_user_model()

from django.db import transaction
from django.db.models import Q, Avg, F, ExpressionWrapper, DurationField
from rest_framework import viewsets, permissions, status, generics, views
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from .models import (
    HelpCategory, HelpArticle, FAQ, BannerPromo,
    ContactInfo, SupportInfo, ChatQuickReply, SupportTicket,
    Complaint, ReportProduct, ReportSeller, ReportBuyer,
    Dispute, InternalNote,
)
from drf_spectacular.utils import extend_schema
from .serializers import (
    HelpCategorySerializer, HelpArticleListSerializer, HelpArticleDetailSerializer,
    FAQSerializer, BannerPromoSerializer, ContactInfoSerializer,
    SupportInfoSerializer, ChatQuickReplySerializer, SupportTicketSerializer,
    SupportTicketDetailSerializer, TicketAssignSerializer,
    ComplaintSerializer, ReportProductSerializer, ReportSellerSerializer,
    ReportBuyerSerializer, DisputeSerializer, InternalNoteSerializer,
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
        
        from django.conf import settings
        if not settings.AI_CHAT_ENABLED:
            return Response(
                {'error': 'AI chat service is currently unavailable.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        try:
            ai_service = get_ai_chat_service()
            response_text, confidence, should_escalate = ai_service.generate_response(
                query=query,
                customer_id=customer_id,
                stream=stream
            )
            response_data = {
                'response': response_text,
                'confidence': round(confidence, 2),
                'escalated': should_escalate,
            }
            if should_escalate:
                response_data['message'] = (
                    'Tim support kami akan segera menghubungi Anda untuk bantuan lebih lanjut.'
                )
                if customer_id:
                    SupportTicket.objects.create(
                        user_id=customer_id,
                        subject=f'AI Escalation: {query[:50]}',
                        message=response_text,
                        priority='high' if confidence < 0.5 else 'medium',
                        support_status='open',
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


# =============================================================================
# CUSTOMER SUPPORT CENTER VIEWS
# =============================================================================


class SupportDashboardView(views.APIView):
    """Admin support center dashboard with real-time stats."""
    permission_classes = (permissions.IsAdminUser,)

    def get(self, request):
        from django.utils import timezone
        from datetime import timedelta
        from django.db.models import Avg, Count, Q

        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)

        tickets = SupportTicket.objects.all()
        tickets_30d = tickets.filter(created_at__gte=thirty_days_ago)

        # Response time — compute avg hours between created_at and first_response_at
        response_result = tickets_30d.exclude(
            first_response_at__isnull=True
        ).annotate(
            response_duration=ExpressionWrapper(
                F('first_response_at') - F('created_at'),
                output_field=DurationField()
            )
        ).aggregate(avg_duration=Avg('response_duration'))

        avg_duration = response_result['avg_duration']
        avg_resp_hours = round(avg_duration.total_seconds() / 3600, 1) if avg_duration else 0

        stats = {
            'total_tickets': tickets.count(),
            'open_tickets': tickets.filter(support_status='open').count(),
            'pending_tickets': tickets.filter(support_status='pending').count(),
            'solved_tickets': tickets.filter(support_status='solved').count(),
            'urgent_tickets': tickets.filter(priority='urgent', support_status__in=['open', 'pending']).count(),
            'unassigned_tickets': tickets.filter(assigned_to__isnull=True, support_status__in=['open', 'pending']).count(),
            'avg_response_time_hours': round(float(response_times.aggregate(
                avg=Avg('first_response_at')
            )['avg'] or 0), 1),
            'sla_breach_count': tickets_30d.filter(sla_met=False, sla_deadline__lt=now).count(),
            'total_complaints': Complaint.objects.count(),
            'pending_complaints': Complaint.objects.filter(status='pending').count(),
            'total_reports': ReportProduct.objects.count() + ReportSeller.objects.count() + ReportBuyer.objects.count(),
            'pending_reports': ReportProduct.objects.filter(status='pending').count() + \
                               ReportSeller.objects.filter(status='pending').count() + \
                               ReportBuyer.objects.filter(status='pending').count(),
        }
        return Response(stats)


class SupportTicketAssignView(views.APIView):
    """Assign a support ticket to an admin."""
    permission_classes = (permissions.IsAdminUser,)

    @transaction.atomic
    def post(self, request, pk):
        try:
            ticket = SupportTicket.objects.get(pk=pk)
        except SupportTicket.DoesNotExist:
            return Response({'error': 'Ticket not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = TicketAssignSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        admin_id = serializer.validated_data['assigned_to_id']
        try:
            admin_user = User.objects.get(pk=admin_id, is_staff=True)
        except User.DoesNotExist:
            return Response({'error': 'Admin not found'}, status=status.HTTP_404_NOT_FOUND)

        ticket.assign_to(admin_user)

        # Create internal note
        note_text = serializer.validated_data.get('note', '')
        if note_text:
            InternalNote.objects.create(
                note_type='ticket',
                reference_id=ticket.id,
                author=request.user,
                content=note_text
            )

        # Create audit log
        from accounts.models import AdminAuditLog
        AdminAuditLog.objects.create(
            admin=request.user,
            admin_email=request.user.email,
            action='update_admin',
            description=f'Assigned ticket #{ticket.id} to {admin_user.full_name}',
            target_user=admin_user,
            details={'ticket_id': ticket.id, 'assigned_to': admin_user.email}
        )

        return Response(SupportTicketDetailSerializer(ticket).data)


class SupportTicketResolveView(views.APIView):
    """Resolve or close a support ticket."""
    permission_classes = (permissions.IsAdminUser,)

    def post(self, request, pk):
        try:
            ticket = SupportTicket.objects.get(pk=pk)
        except SupportTicket.DoesNotExist:
            return Response({'error': 'Ticket not found'}, status=status.HTTP_404_NOT_FOUND)

        action = request.data.get('action', 'resolve')
        if action == 'resolve':
            ticket.resolve()
        elif action == 'close':
            ticket.close()
        else:
            return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'status': 'ok', 'new_status': ticket.support_status})


class ComplaintListView(generics.ListCreateAPIView):
    """List and create complaints."""
    serializer_class = ComplaintSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Complaint.objects.none()
        if self.request.user.is_staff:
            return Complaint.objects.all()
        return Complaint.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        complaint = serializer.save(user=self.request.user)
        # Notify admins about new complaint
        from notifications.services import notify_system
        from accounts.models import AdminAuditLog
        admin_staff = User.objects.filter(is_staff=True, is_active=True)[:5]
        for admin in admin_staff:
            notify_system(
                user_id=admin.id,
                title='Komplain Baru',
                description=f'Komplain #{complaint.id}: {complaint.get_complaint_type_display()} dari {complaint.user.full_name}',
                action_url='/admin-panel/support/',
                priority='high' if complaint.status == 'pending' else 'medium',
                action_text='Lihat Komplain',
            )
        # Audit log
        AdminAuditLog.objects.create(
            admin=self.request.user if self.request.user.is_staff else None,
            admin_email=self.request.user.email,
            action='update_admin',
            description=f'Membuat komplain #{complaint.id}: {complaint.get_complaint_type_display()}',
            details={'complaint_id': complaint.id, 'type': complaint.complaint_type}
        )


class ComplaintDetailView(generics.RetrieveUpdateAPIView):
    """Retrieve or update a complaint."""
    serializer_class = ComplaintSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        if self.request.user.is_staff:
            return Complaint.objects.all()
        return Complaint.objects.filter(user=self.request.user)


class ReportProductListView(generics.ListCreateAPIView):
    """List and create product reports."""
    serializer_class = ReportProductSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ReportProduct.objects.none()
        if self.request.user.is_staff:
            return ReportProduct.objects.all()
        return ReportProduct.objects.filter(reporter=self.request.user)

    def perform_create(self, serializer):
        serializer.save(reporter=self.request.user)


class ReportProductModerateView(views.APIView):
    """Moderate a product report (admin only)."""
    permission_classes = (permissions.IsAdminUser,)

    @transaction.atomic
    def post(self, request, pk):
        try:
            report = ReportProduct.objects.select_related('product').get(pk=pk)
        except ReportProduct.DoesNotExist:
            return Response({'error': 'Report not found'}, status=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get('status')
        notes = request.data.get('notes', '')

        if new_status not in ['approved', 'rejected']:
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)

        report.status = new_status
        report.moderated_by = request.user
        report.moderation_notes = notes
        report.save()

        # If approved, flag the product
        if new_status == 'approved':
            report.product.is_active = False
            report.product.save(update_fields=['is_active'])

        # Notify reporter about moderation result
        from notifications.services import notify_system
        notify_system(
            user_id=report.reporter_id,
            title=f'Laporan Produk {new_status.title()}',
            description=f'Laporan Anda terhadap {report.product.name} telah {new_status}.' if new_status == 'approved' else f'Laporan Anda terhadap {report.product.name} ditolak.',
            action_url='/support/',
        )
        # Audit log
        from accounts.models import AdminAuditLog
        AdminAuditLog.objects.create(
            admin=request.user,
            admin_email=request.user.email,
            action='update_admin',
            description=f'Moderasi laporan produk #{report.id}: {new_status}',
            target_user=report.reporter,
            details={'report_id': report.id, 'product': str(report.product), 'status': new_status}
        )

        return Response(ReportProductSerializer(report).data)


class ReportSellerListView(generics.ListCreateAPIView):
    """List and create seller reports."""
    serializer_class = ReportSellerSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ReportSeller.objects.none()
        if self.request.user.is_staff:
            return ReportSeller.objects.all()
        return ReportSeller.objects.filter(reporter=self.request.user)

    def perform_create(self, serializer):
        serializer.save(reporter=self.request.user)


class ReportBuyerListView(generics.ListCreateAPIView):
    """List and create buyer reports."""
    serializer_class = ReportBuyerSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ReportBuyer.objects.none()
        if self.request.user.is_staff:
            return ReportBuyer.objects.all()
        return ReportBuyer.objects.filter(reporter=self.request.user)

    def perform_create(self, serializer):
        serializer.save(reporter=self.request.user)


class DisputeListView(generics.ListCreateAPIView):
    """List and create disputes."""
    serializer_class = DisputeSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Dispute.objects.none()
        user = self.request.user
        if user.is_staff:
            return Dispute.objects.all()
        return Dispute.objects.filter(Q(opened_by=user) | Q(against_user=user))


class DisputeDetailView(generics.RetrieveUpdateAPIView):
    """Retrieve or update a dispute."""
    serializer_class = DisputeSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Dispute.objects.all()
        return Dispute.objects.filter(Q(opened_by=user) | Q(against_user=user))


class DisputeResolveView(views.APIView):
    """Resolve a dispute (admin/mediator only)."""
    permission_classes = (permissions.IsAdminUser,)

    @transaction.atomic
    def post(self, request, pk):
        try:
            dispute = Dispute.objects.get(pk=pk)
        except Dispute.DoesNotExist:
            return Response({'error': 'Dispute not found'}, status=status.HTTP_404_NOT_FOUND)

        resolution = request.data.get('resolution')
        notes = request.data.get('notes', '')

        if resolution not in ['buyer_win', 'seller_win', 'partial', 'cancelled']:
            return Response({'error': 'Invalid resolution'}, status=status.HTTP_400_BAD_REQUEST)

        from django.utils import timezone
        dispute.status = 'resolved'
        dispute.resolution = resolution
        dispute.resolution_notes = notes
        dispute.mediator = request.user
        dispute.resolved_at = timezone.now()
        dispute.save()

        # Notify parties about resolution
        from notifications.services import notify_system
        notify_system(
            user_id=dispute.opened_by_id,
            title='Sengketa Terselesaikan',
            description=f'Sengketa #{dispute.id} telah diselesaikan: {dispute.get_resolution_display()}',
            action_url='/admin-panel/support/',
        )
        # Audit log
        from accounts.models import AdminAuditLog
        AdminAuditLog.objects.create(
            admin=request.user,
            admin_email=request.user.email,
            action='update_admin',
            description=f'Menyelesaikan sengketa #{dispute.id}: {dispute.get_resolution_display()}',
            details={'dispute_id': dispute.id, 'resolution': resolution}
        )

        return Response(DisputeSerializer(dispute).data)


class InternalNoteListView(generics.ListCreateAPIView):
    """List and create internal notes."""
    serializer_class = InternalNoteSerializer
    permission_classes = (permissions.IsAdminUser,)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return InternalNote.objects.none()
        qs = InternalNote.objects.all()
        note_type = self.request.query_params.get('note_type')
        reference_id = self.request.query_params.get('reference_id')
        if note_type:
            qs = qs.filter(note_type=note_type)
        if reference_id:
            qs = qs.filter(reference_id=reference_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
