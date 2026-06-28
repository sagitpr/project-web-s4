"""Shared pytest fixtures for Warungio Django tests."""

import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from stores.models import Store, StoreCategory

User = get_user_model()

PASSWORD = "TestPass123!"


@pytest.fixture
def api_client():
    """Return an unauthenticated DRF APIClient."""
    return APIClient()


@pytest.fixture
def authed_client(verified_user):
    """Return an authenticated DRF APIClient as a verified user."""
    client = APIClient()
    client.force_authenticate(user=verified_user)
    return client


@pytest.fixture
def verified_user(db):
    """Create and return a verified user."""
    user = User.objects.create_user(
        "verified",
        email="verified@test.io",
        password=PASSWORD,
        full_name="Verified User",
        is_verified=True,
    )
    return user


@pytest.fixture
def unverified_user(db):
    """Create and return an unverified user."""
    user = User.objects.create_user(
        "unverified",
        email="unverified@test.io",
        password=PASSWORD,
        full_name="Unverified User",
        is_verified=False,
    )
    return user


@pytest.fixture
def seller_user(db):
    """Create and return a verified user who owns a store."""
    user = User.objects.create_user(
        "seller",
        email="seller@test.io",
        password=PASSWORD,
        full_name="Seller User",
        is_verified=True,
        role='seller',
    )
    return user


@pytest.fixture
def buyer_user(db):
    """Create and return a verified buyer user."""
    user = User.objects.create_user(
        "buyer",
        email="buyer@test.io",
        password=PASSWORD,
        full_name="Buyer User",
        is_verified=True,
    )
    return user


@pytest.fixture
def test_category(db):
    """Create and return a store category."""
    return StoreCategory.objects.create(name="Warung Makanan")


@pytest.fixture
def test_store(db, seller_user, test_category):
    """Create and return a store owned by seller_user."""
    store = Store.objects.create(
        user=seller_user,
        store_name="Toko Test Segar",
        slug="toko-test-segar",
        description="Toko untuk testing",
        address="Jl. Testing No. 1",
        city="Jakarta",
        category=test_category,
        status="active",
    )
    return store


@pytest.fixture
def seller_client(seller_user):
    """Return an authenticated client for a seller."""
    client = APIClient()
    client.force_authenticate(user=seller_user)
    return client


@pytest.fixture
def buyer_client(buyer_user):
    """Return an authenticated client for a buyer."""
    client = APIClient()
    client.force_authenticate(user=buyer_user)
    return client
