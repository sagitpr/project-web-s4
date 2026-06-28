"""
Chat app models for Warungio Marketplace.
Real-time messaging between buyers and sellers.
"""

from django.db import models
from django.conf import settings


class Conversation(models.Model):
    """Chat conversation between users."""
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name='conversations'
    )
    store = models.ForeignKey(
        'stores.Store', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='conversations'
    )
    subject = models.CharField(max_length=255, blank=True, null=True)
    
    # Metadata
    last_message = models.TextField(blank=True, null=True)
    last_message_at = models.DateTimeField(null=True, blank=True)
    last_sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='last_messages'
    )
    unread_count = models.IntegerField(default=0)
    
    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'conversations'
        verbose_name = 'Percakapan'
        verbose_name_plural = 'Percakapan'
        indexes = [
            models.Index(fields=['last_message_at']),
        ]

    def __str__(self):
        return f'Conversation #{self.id}'

    def get_other_participant(self, user):
        return self.participants.exclude(id=user.id).first()


class Message(models.Model):
    """Individual chat message."""
    MESSAGE_TYPES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('file', 'File'),
        ('order', 'Order'),
        ('system', 'System'),
    ]

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='sent_messages'
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='received_messages'
    )
    
    # Content
    message_type = models.CharField(
        max_length=20, choices=MESSAGE_TYPES, default='text'
    )
    content = models.TextField(verbose_name='Pesan')
    attachment = models.FileField(
        upload_to='chat/attachments/', blank=True, null=True
    )
    
    # Status
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chats'
        verbose_name = 'Pesan'
        verbose_name_plural = 'Pesan'
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['sender', 'receiver', 'is_read']),
        ]

    def __str__(self):
        return f'Message from {self.sender} - {self.created_at}'

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            # Update conversation metadata
            conv = self.conversation
            conv.last_message = self.content[:200]
            conv.last_message_at = self.created_at
            conv.last_sender = self.sender
            conv.unread_count = conv.messages.filter(
                is_read=False
            ).exclude(sender=self.receiver).count()
            conv.save(update_fields=[
                'last_message', 'last_message_at', 'last_sender', 'unread_count'
            ])
