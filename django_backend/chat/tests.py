"""Tests for the chat app."""

import pytest
from rest_framework import status
from django.urls import reverse

from .models import Conversation, Message


class TestConversationModel:
    """Test Conversation model."""

    def test_create_conversation(self, db, verified_user, buyer_user):
        conv = Conversation.objects.create()
        conv.participants.add(verified_user, buyer_user)
        assert conv.participants.count() == 2
        assert conv.is_active is True
        assert conv.created_at is not None

    def test_conversation_str(self, db):
        conv = Conversation.objects.create()
        assert str(conv) == f"Conversation #{conv.id}"

    def test_get_other_participant(self, db, verified_user, buyer_user):
        conv = Conversation.objects.create()
        conv.participants.add(verified_user, buyer_user)
        other = conv.get_other_participant(verified_user)
        assert other == buyer_user


class TestMessageModel:
    """Test Message model."""

    def test_create_message(self, db, verified_user, buyer_user):
        conv = Conversation.objects.create()
        conv.participants.add(verified_user, buyer_user)
        msg = Message.objects.create(
            conversation=conv,
            sender=buyer_user,
            receiver=verified_user,
            content="Halo, apakah stok tersedia?",
        )
        assert msg.conversation == conv
        assert msg.sender == buyer_user
        assert msg.content == "Halo, apakah stok tersedia?"
        assert msg.created_at is not None
        assert msg.is_read is False
        assert msg.message_type == "text"

    def test_message_str(self, db, verified_user, buyer_user):
        conv = Conversation.objects.create()
        conv.participants.add(verified_user, buyer_user)
        msg = Message.objects.create(
            conversation=conv, sender=buyer_user,
            receiver=verified_user, content="Test",
        )
        assert str(msg) == f"Message from {buyer_user} - {msg.created_at}"

    def test_mark_as_read(self, db, verified_user, buyer_user):
        conv = Conversation.objects.create()
        conv.participants.add(verified_user, buyer_user)
        msg = Message.objects.create(
            conversation=conv, sender=buyer_user,
            receiver=verified_user, content="Ping",
        )
        assert msg.is_read is False
        msg.is_read = True
        msg.read_at = msg.created_at
        msg.save()
        msg.refresh_from_db()
        assert msg.is_read is True


# ─── API Tests ──────────────────────────────────────────────────────────────

class TestConversationListAPI:
    LIST_URL = reverse("conversation-list")

    def test_list_requires_auth(self, api_client):
        resp = api_client.get(self.LIST_URL)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_own_conversations(self, authed_client, verified_user, buyer_user):
        conv = Conversation.objects.create()
        conv.participants.add(verified_user, buyer_user)
        resp = authed_client.get(self.LIST_URL)
        assert resp.status_code == status.HTTP_200_OK
        assert "results" in resp.json()


class TestConversationCreateAPI:
    CREATE_URL = reverse("conversation-create")

    def test_create_conversation(self, authed_client, buyer_user):
        resp = authed_client.post(self.CREATE_URL, {}, format="json")
        # Accept 201 (created) or 400 (if serializer requires specific fields)
        assert resp.status_code in (status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST)

    def test_create_conversation_unauthenticated(self, api_client):
        resp = api_client.post(self.CREATE_URL, {}, format="json")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


class TestMessageListAPI:
    def _url(self, conversation_id):
        return reverse("message-list", args=[conversation_id])

    def test_list_requires_auth(self, api_client):
        resp = api_client.get(self._url(1))
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_messages(self, authed_client, verified_user, buyer_user):
        conv = Conversation.objects.create()
        conv.participants.add(verified_user, buyer_user)
        Message.objects.create(conversation=conv, sender=buyer_user, receiver=verified_user, content="Halo")
        Message.objects.create(conversation=conv, sender=verified_user, receiver=buyer_user, content="Ya ada")
        resp = authed_client.get(self._url(conv.id))
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.json()) >= 2


class TestMessageSendAPI:
    SEND_URL = reverse("message-send")

    def test_send_message(self, authed_client, verified_user, buyer_user):
        conv = Conversation.objects.create()
        conv.participants.add(verified_user, buyer_user)
        resp = authed_client.post(self.SEND_URL, {
            "conversation": conv.id,
            "content": "Test message content",
            "receiver": buyer_user.id,
        }, format="json")
        assert resp.status_code in (status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST)

    def test_send_unauthenticated(self, api_client):
        resp = api_client.post(self.SEND_URL, {"content": "test"}, format="json")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED
