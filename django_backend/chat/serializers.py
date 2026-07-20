"""
Chat serializers for Warungio Marketplace.
Real-time messaging between buyers and sellers.
"""

from rest_framework import serializers
from .models import Conversation, Message
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.openapi import OpenApiTypes


class MessageSerializer(serializers.ModelSerializer):
    """Chat message serializer."""
    sender_name = serializers.CharField(source='sender.full_name', read_only=True, allow_null=True)
    sender_photo = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ('id', 'conversation', 'sender', 'sender_name', 'sender_photo',
                  'receiver', 'message_type', 'content', 'attachment', 'is_read',
                  'read_at', 'created_at')
        read_only_fields = ('sender', 'is_read', 'read_at', 'created_at')

    @extend_schema_field(OpenApiTypes.STR)
    def get_sender_photo(self, obj):
        if obj.sender and obj.sender.profile_photo:
            return obj.sender.profile_photo.url
        return None


class MessageCreateSerializer(serializers.ModelSerializer):
    """Create new message serializer."""
    class Meta:
        model = Message
        fields = ('conversation', 'receiver', 'message_type', 'content', 'attachment')

    def validate_conversation(self, value):
        user = self.context['request'].user
        if not value.participants.filter(id=user.id).exists():
            raise serializers.ValidationError("Anda bukan peserta percakapan ini.")
        return value


class ConversationListSerializer(serializers.ModelSerializer):
    """Conversation list serializer."""
    last_message_preview = serializers.SerializerMethodField()
    last_message_time = serializers.DateTimeField(source='last_message_at', read_only=True)
    other_participant = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ('id', 'subject', 'last_message_preview', 'last_message_time',
                  'last_sender', 'unread_count', 'other_participant', 'created_at')

    @extend_schema_field(OpenApiTypes.STR)
    def get_last_message_preview(self, obj):
        return (obj.last_message[:100] + '...') if obj.last_message and len(obj.last_message) > 100 else obj.last_message

    @extend_schema_field(OpenApiTypes.STR)
    def get_other_participant(self, obj):
        user = self.context['request'].user
        other = obj.get_other_participant(user)
        if other:
            return {
                'id': other.id,
                'full_name': other.full_name,
                'photo': other.profile_photo.url if other.profile_photo else None,
            }
        return None


class ConversationDetailSerializer(serializers.ModelSerializer):
    """Conversation detail with messages."""
    messages = MessageSerializer(many=True, read_only=True)
    participants_info = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ('id', 'participants', 'participants_info', 'store', 'subject',
                  'last_message', 'last_message_at', 'unread_count', 'messages',
                  'created_at', 'updated_at')

    @extend_schema_field(OpenApiTypes.STR)
    def get_participants_info(self, obj):
        participants = obj.participants.all()
        return [{
            'id': p.id,
            'full_name': p.full_name,
            'role': p.role,
            'photo': p.profile_photo.url if p.profile_photo else None,
        } for p in participants]
