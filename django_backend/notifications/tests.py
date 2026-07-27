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


# ─── New View Tests ──────────────────────────────────────────────────────────

class TestNotificationArchiveAPI:
    """Test NotificationArchiveView."""
    URL = reverse("notification-archive")

    def test_archive_requires_auth(self, api_client):
        resp = api_client.post(self.URL, {'notification_ids': [1]}, format='json')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_archive_single(self, authed_client, verified_user):
        n = Notification.objects.create(
            user=verified_user, title="Arsipkan",
            description="Test", notification_type="system",
        )
        resp = authed_client.post(self.URL, {
            'notification_ids': [n.id], 'archive': True
        }, format='json')
        assert resp.status_code == status.HTTP_200_OK
        n.refresh_from_db()
        assert n.is_archived is True

    def test_unarchive(self, authed_client, verified_user):
        n = Notification.objects.create(
            user=verified_user, title="Pulihkan",
            description="Test", notification_type="system",
            is_archived=True,
        )
        resp = authed_client.post(self.URL, {
            'notification_ids': [n.id], 'archive': False
        }, format='json')
        assert resp.status_code == status.HTTP_200_OK
        n.refresh_from_db()
        assert n.is_archived is False

    def test_archive_other_user_not_affected(self, db, verified_user, buyer_user):
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=buyer_user)
        n = Notification.objects.create(
            user=verified_user, title="Bukan punyamu",
            description="Test", notification_type="system",
        )
        resp = client.post(self.URL, {
            'notification_ids': [n.id], 'archive': True
        }, format='json')
        assert resp.status_code == status.HTTP_200_OK
        n.refresh_from_db()
        assert n.is_archived is False


class TestNotificationDeleteBulkAPI:
    """Test NotificationDeleteBulkView."""
    URL = reverse("notification-delete-bulk")

    def test_delete_bulk(self, authed_client, verified_user):
        n1 = Notification.objects.create(
            user=verified_user, title="Hapus 1",
            description="Test", notification_type="system",
        )
        n2 = Notification.objects.create(
            user=verified_user, title="Hapus 2",
            description="Test", notification_type="system",
        )
        resp = authed_client.delete(self.URL, {
            'notification_ids': [n1.id, n2.id]
        }, format='json')
        assert resp.status_code == status.HTTP_200_OK
        assert Notification.objects.filter(id__in=[n1.id, n2.id]).count() == 0

    def test_delete_requires_auth(self, api_client):
        resp = api_client.delete(self.URL, {
            'notification_ids': [1]
        }, format='json')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_delete_other_user_not_affected(self, db, verified_user, buyer_user):
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=buyer_user)
        n = Notification.objects.create(
            user=verified_user, title="Jangan hapus",
            description="Test", notification_type="system",
        )
        resp = client.delete(self.URL, {
            'notification_ids': [n.id]
        }, format='json')
        assert resp.status_code == status.HTTP_200_OK
        assert Notification.objects.filter(id=n.id).count() == 1  # Still exists


class TestNotificationBroadcastAPI:
    """Test NotificationBroadcastView."""
    BROADCAST_URL = reverse("notification-broadcast")
    ARCHIVE_URL = reverse("notification-archive")
    DELETE_BULK_URL = reverse("notification-delete-bulk")

    def test_broadcast_requires_admin(self, authed_client):
        """Non-admin users cannot broadcast."""
        resp = authed_client.post(self.BROADCAST_URL, {
            'title': 'Test', 'description': 'Test',
        }, format='json')
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_broadcast_requires_auth(self, api_client):
        resp = api_client.post(self.BROADCAST_URL, {
            'title': 'Test', 'description': 'Test',
        }, format='json')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_broadcast_success(self, api_client, db, verified_user):
        """Admin can broadcast to all users."""
        from rest_framework.test import APIClient
        from accounts.models import User
        # Manually create admin user
        admin = User.objects.create_superuser(
            email='admin@test.com',
            password='admin123',
            username='admin',
        )
        client = APIClient()
        client.force_authenticate(user=admin)
        
        resp = client.post(self.BROADCAST_URL, {
            'title': 'Test Broadcast',
            'description': 'Test deskripsi',
            'target_role': 'all',
            'notification_type': 'system',
        }, format='json')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data['sent_count'] >= 1
        assert data['target_role'] == 'all'

    def test_broadcast_by_role(self, api_client, db, verified_user):
        """Broadcast to specific role."""
        from rest_framework.test import APIClient
        from accounts.models import User
        admin = User.objects.create_superuser(
            email='admin2@test.com',
            password='admin123',
            username='admin2',
        )
        client = APIClient()
        client.force_authenticate(user=admin)
        
        resp = client.post(self.BROADCAST_URL, {
            'title': 'Test Broadcast',
            'description': 'Test deskripsi',
            'target_role': 'buyer',
            'notification_type': 'promo',
            'action_url': '/buyer/promo/',
            'action_text': 'Lihat Promo',
        }, format='json')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data['sent_count'] >= 0
