"""
Chat views for Warungio Marketplace.
Conversation management and messaging API.
"""

from django.db.models import Q
from rest_framework import status, generics, permissions, views
from rest_framework.response import Response

from .models import Conversation, Message
from .serializers import (
    ConversationListSerializer, ConversationDetailSerializer,
    MessageSerializer, MessageCreateSerializer
)


class ConversationListView(generics.ListAPIView):
    """List user's conversations."""
    serializer_class = ConversationListSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return Conversation.objects.filter(
            participants=self.request.user
        ).order_by('-last_message_at')


class ConversationCreateView(generics.CreateAPIView):
    """Create a new conversation."""
    serializer_class = ConversationDetailSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def perform_create(self, serializer):
        conversation = serializer.save()
        conversation.participants.add(self.request.user)


class ConversationDetailView(generics.RetrieveAPIView):
    """Get conversation with messages."""
    serializer_class = ConversationDetailSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return Conversation.objects.filter(participants=self.request.user)

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        # Mark unread messages as read
        conversation = self.get_object()
        Message.objects.filter(
            conversation=conversation,
            receiver=request.user,
            is_read=False
        ).update(is_read=True)
        return response


class MessageListView(generics.ListAPIView):
    """List messages in a conversation."""
    serializer_class = MessageSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        conv_id = self.kwargs['conversation_id']
        return Message.objects.filter(
            conversation_id=conv_id,
            conversation__participants=self.request.user
        ).order_by('created_at')


class MessageCreateView(generics.CreateAPIView):
    """Send a new message."""
    serializer_class = MessageCreateSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)


class UnreadCountView(views.APIView):
    """Get unread message count."""
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        count = Message.objects.filter(
            receiver=request.user,
            is_read=False
        ).count()
        return Response({'unread_count': count})


class StartConversationView(views.APIView):
    """Start or get existing conversation with another user."""
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        receiver_id = request.data.get('receiver_id')
        message = request.data.get('message', '')
        
        if not receiver_id:
            return Response({'error': 'Receiver ID diperlukan.'},
                          status=status.HTTP_400_BAD_REQUEST)
        
        if int(receiver_id) == request.user.id:
            return Response({'error': 'Tidak bisa chat dengan diri sendiri.'},
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Find existing conversation
        conversation = Conversation.objects.filter(
            participants=request.user
        ).filter(
            participants__id=receiver_id
        ).first()
        
        if not conversation:
            conversation = Conversation.objects.create()
            conversation.participants.add(request.user, receiver_id)
        
        # Send initial message
        if message:
            Message.objects.create(
                conversation=conversation,
                sender=request.user,
                receiver_id=receiver_id,
                content=message,
            )
        
        return Response(
            ConversationDetailSerializer(conversation, context={'request': request}).data
        )
