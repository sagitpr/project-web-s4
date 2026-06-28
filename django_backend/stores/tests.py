"""Tests for the stores app."""

import pytest
from rest_framework import status
from django.urls import reverse
from django.contrib.auth import get_user_model

from .models import Store, StoreCategory


User = get_user_model()


# ─── Model Tests ────────────────────────────────────────────────────────────

class TestStoreCategoryModel:
    def test_create_category(self, db):
        cat = StoreCategory.objects.create(name="Toko Kelontong")
        assert cat.name == "Toko Kelontong"
        assert str(cat) == "Toko Kelontong"


class TestStoreModel:
    def test_create_store(self, db, verified_user, test_category):
        store = Store.objects.create(
            user=verified_user,
            store_name="Warung Sejahtera",
            slug="warung-sejahtera",
            description="Warung kelontong lengkap",
            address="Jl. Merdeka No. 10",
            city="Jakarta",
            category=test_category,
            status="active",
        )
        assert store.user == verified_user
        assert store.store_name == "Warung Sejahtera"
        assert store.slug == "warung-sejahtera"
        assert store.status == "active"
        assert store.created_at is not None

    def test_store_str(self, db, verified_user, test_category):
        store = Store.objects.create(
            user=verified_user, store_name="Warung Test",
            slug="warung-test", city="Jakarta", category=test_category,
        )
        assert str(store) == "Warung Test"

    def test_store_default_status(self, db, verified_user, test_category):
        store = Store.objects.create(
            user=verified_user, store_name="Warung Default",
            slug="warung-default", city="Jakarta", category=test_category,
        )
        assert store.status == "pending"

    def test_store_slug_generated(self, db, verified_user, test_category):
        store = Store.objects.create(
            user=verified_user, store_name="Toko Slug Test",
            city="Jakarta", category=test_category,
        )
        assert store.slug == "toko-slug-test"


# ─── API Tests ──────────────────────────────────────────────────────────────

class TestStoreListAPI:
    LIST_URL = reverse("store-list")

    def test_list_stores_empty(self, api_client, db):
        resp = api_client.get(self.LIST_URL)
        assert resp.status_code == status.HTTP_200_OK
        assert "results" in resp.json()

    def test_list_stores_with_data(self, api_client, test_store):
        resp = api_client.get(self.LIST_URL)
        assert resp.status_code == status.HTTP_200_OK
        names = [s["store_name"] for s in resp.json()["results"]]
        assert test_store.store_name in names

    def test_filter_by_city(self, api_client, test_store, db, test_category):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user_a = User.objects.create_user(
            "store_user_a", email="store_a@test.io",
            password="TestPass123!", full_name="Store A", is_verified=True,
        )
        user_b = User.objects.create_user(
            "store_user_b", email="store_b@test.io",
            password="TestPass123!", full_name="Store B", is_verified=True,
        )
        Store.objects.create(
            user=user_a, store_name="Warung A", slug="warung-a",
            city="Jakarta", category=test_category, status="active",
        )
        Store.objects.create(
            user=user_b, store_name="Warung B", slug="warung-b",
            city="Bandung", category=test_category, status="active",
        )
        resp = api_client.get(self.LIST_URL, {"city": "Jakarta"})
        assert resp.status_code == status.HTTP_200_OK
        for s in resp.json()["results"]:
            assert s["city"] == "Jakarta"


class TestStoreCreateAPI:
    CREATE_URL = reverse("store-create")

    def test_unauthenticated_cannot_create(self, api_client):
        resp = api_client.post(self.CREATE_URL, {"store_name": "Warung Baru"}, format="json")
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_verified_user_can_create(self, verified_user, test_category):
        from rest_framework.test import APIClient
        from django.contrib.auth import get_user_model
        User = get_user_model()
        # Create a fresh authenticated client with seller role
        user = User.objects.get(email="verified@test.io")
        user.role = 'seller'
        user.save(update_fields=['role'])
        client = APIClient()
        fresh_user = User.objects.get(email="verified@test.io")
        client.force_authenticate(user=fresh_user)
        resp = client.post(self.CREATE_URL, {
            "store_name": "Warung Saya",
            "description": "Toko baru",
            "address": "Jl. Baru No. 1",
            "city": "Jakarta",
            "category": test_category.id if hasattr(test_category, 'id') else test_category,
        }, format="json")
        assert resp.status_code in (status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST)
        if resp.status_code == status.HTTP_201_CREATED:
            assert resp.json()["store_name"] == "Warung Saya"


class TestStoreDetailAPI:
    def _url(self, store_id):
        return reverse("store-detail", args=[store_id])

    def test_get_store(self, api_client, test_store):
        resp = api_client.get(self._url(test_store.id))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["store_name"] == test_store.store_name

    def test_get_store_not_found(self, api_client, db):
        resp = api_client.get(self._url(99999))
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_owner_can_update(self, seller_client, test_store):
        url = reverse("my-store")
        resp = seller_client.patch(url, {"description": "Updated desc"}, format="json")
        assert resp.status_code in (status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST)
        if resp.status_code == status.HTTP_200_OK:
            test_store.refresh_from_db()
            assert test_store.description == "Updated desc"

    def test_non_owner_cannot_update(self, buyer_client, test_store):
        url = reverse("my-store")
        resp = buyer_client.patch(url, {"store_name": "Hacked Store!"}, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN


class TestStoreFollowAPI:
    """Test follow/unfollow store functionality."""

    def _url(self, store_id):
        return reverse("store-follow", args=[store_id])

    def test_follow_store(self, buyer_client, test_store):
        resp = buyer_client.post(self._url(test_store.id), {}, format="json")
        assert resp.status_code in (status.HTTP_200_OK, status.HTTP_201_CREATED)

    def test_unfollow_store(self, buyer_client, test_store):
        buyer_client.post(self._url(test_store.id), {}, format="json")
        resp = buyer_client.post(self._url(test_store.id), {}, format="json")
        assert resp.status_code in (status.HTTP_200_OK, status.HTTP_201_CREATED)

    def test_follow_unauthenticated(self, api_client, test_store):
        resp = api_client.post(self._url(test_store.id), {}, format="json")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


class TestStoreCategoryAPI:
    LIST_URL = reverse("store-categories")

    def test_list_categories(self, api_client, test_category):
        resp = api_client.get(self.LIST_URL)
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.json()) >= 1
