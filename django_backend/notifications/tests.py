"""Tests for the notifications app."""

import pytest
from rest_framework import status
from django.urls import reverse

from .models import Notification, NotificationPreference


class TestNotificationModel:
    """Test Notification model."""

    def test_create_notification(self, db, verified_user):
        notification = Notification.objects.create(
            user=verified_user,
            title="Pesanan Baru",
            description="Anda menerima pesanan baru #123",
            notification_type="order",
        )
        assert notification.user == verified_user
        assert notification.title == "Pesanan Baru"
        assert notification.description == "Anda menerima pesanan baru #123"
        assert notification.notification_type == "order"
        assert notification.is_read is False
        assert notification.priority == "medium"
        assert notification.created_at is not None

    def test_notification_str(self, db, verified_user):
        notification = Notification.objects.create(
            user=verified_user,
            title="Test Notif",
            description="Test",
            notification_type="system",
        )
        assert str(notification) == f"Test Notif - {verified_user.email}"

    def test_default_is_read(self, db, verified_user):
        notification = Notification.objects.create(
            user=verified_user,
            title="Judul", description="Pesan",
            notification_type="promo",
        )
        assert notification.is_read is False

    def test_mark_as_read(self, db, verified_user):
        notification = Notification.objects.create(
            user=verified_user,
            title="Dibaca", description="Notif ini akan dibaca",
            notification_type="system",
        )
        notification.mark_as_read()
        notification.refresh_from_db()
        assert notification.is_read is True
        assert notification.read_at is not None

    def test_notification_type_choices(self, db, verified_user):
        for ntype in ["order", "payment", "chat", "promo", "system", "follow", "review", "product"]:
            notification = Notification.objects.create(
                user=verified_user,
                title=f"Type {ntype}",
                description=f"Testing type {ntype}",
                notification_type=ntype,
            )
            assert notification.notification_type == ntype


class TestNotificationPreferenceModel:
    def test_create_prefs(self, db, verified_user):
        prefs = NotificationPreference.objects.create(user=verified_user)
        assert prefs.user == verified_user
        assert prefs.push_orders is True
        assert prefs.email_orders is True
        assert prefs.sms_otp is True
        assert str(prefs) == f"Notification prefs for {verified_user.email}"


# ─── API Tests ──────────────────────────────────────────────────────────────

class TestNotificationListAPI:
    LIST_URL = reverse("notification-list")

    def test_list_requires_auth(self, api_client):
        resp = api_client.get(self.LIST_URL)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_notifications(self, authed_client, verified_user):
        Notification.objects.create(
            user=verified_user, title="Notif 1",
            description="Pesan 1", notification_type="system",
        )
        Notification.objects.create(
            user=verified_user, title="Notif 2",
            description="Pesan 2", notification_type="order",
        )
        resp = authed_client.get(self.LIST_URL)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert len(data["results"]) >= 2

    def test_list_other_user_notifications(self, db, verified_user, buyer_user):
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=buyer_user)
        Notification.objects.create(
            user=verified_user, title="Notif Rahasia",
            description="Rahasia", notification_type="system",
        )
        resp = client.get(self.LIST_URL)
        assert resp.status_code == status.HTTP_200_OK
        titles = [n["title"] for n in resp.json()["results"]]
        assert "Notif Rahasia" not in titles


class TestNotificationMarkReadAPI:
    def test_mark_single_read(self, authed_client, verified_user):
        notification = Notification.objects.create(
            user=verified_user, title="Baca ini",
            description="Segera", notification_type="system",
        )
        url = reverse("notification-mark-read")
        resp = authed_client.post(url, {"notification_ids": [notification.id]}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        notification.refresh_from_db()
        assert notification.is_read is True

    def test_mark_all_read(self, authed_client, verified_user):
        for i in range(3):
            Notification.objects.create(
                user=verified_user, title=f"Notif {i}",
                description=f"Pesan {i}", notification_type="system",
            )
        url = reverse("notification-mark-read")
        resp = authed_client.post(url, {"mark_all": True}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        unread = Notification.objects.filter(user=verified_user, is_read=False).count()
        assert unread == 0

    def test_mark_read_other_user_not_affected(self, db, verified_user, buyer_user):
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=buyer_user)
        notification = Notification.objects.create(
            user=verified_user, title="Bukan punyamu",
            description="Dilarang", notification_type="system",
        )
        # Mark all for other user shouldn't affect verified_user's notification
        url = reverse("notification-mark-read")
        resp = client.post(url, {"mark_all": True}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        notification.refresh_from_db()
        assert notification.is_read is False


class TestNotificationUnreadCountAPI:
    URL = reverse("notification-unread-count")

    def test_unread_count(self, authed_client, verified_user):
        Notification.objects.create(
            user=verified_user, title="Notif Unread",
            description="Belum dibaca", notification_type="system",
        )
        resp = authed_client.get(self.URL)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["total_unread"] >= 1
