"""
Shared pytest fixtures for all Warungio app tests.

Provides: api_client, verified_user, seller_client, buyer_client,
          test_category, test_store
"""

import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def api_client():
    """Provide a bare API client (unauthenticated)."""
    return APIClient()


@pytest.fixture
def verified_user(db):
    """Create and return a verified buyer user (default test user)."""
    user, _ = User.objects.get_or_create(
        email='verified@test.io',
        defaults={
            'username': 'verified_user',
            'full_name': 'Verified User',
            'is_verified': True,
            'is_active': True,
            'role': 'buyer',
        },
    )
    if not user.check_password('TestPass123!'):
        user.set_password('TestPass123!')
        user.save(update_fields=['password'])
    return user


@pytest.fixture
def seller_user(db):
    """Create and return a verified seller user (store owner for tests)."""
    user, _ = User.objects.get_or_create(
        email='seller@test.io',
        defaults={
            'username': 'seller_user',
            'full_name': 'Seller User',
            'is_verified': True,
            'is_active': True,
            'role': 'seller',
        },
    )
    if not user.check_password('TestPass123!'):
        user.set_password('TestPass123!')
        user.save(update_fields=['password'])
    return user


@pytest.fixture
def buyer_user(db):
    """Create and return a verified buyer user (follower for tests)."""
    user, _ = User.objects.get_or_create(
        email='buyer@test.io',
        defaults={
            'username': 'buyer_user',
            'full_name': 'Buyer User',
            'is_verified': True,
            'is_active': True,
            'role': 'buyer',
        },
    )
    return user


@pytest.fixture
def test_category(db):
    """Create and return a StoreCategory for tests."""
    from stores.models import StoreCategory
    cat, _ = StoreCategory.objects.get_or_create(
        name='Toko Kelontong',
    )
    return cat


@pytest.fixture
def test_store(db, seller_user, test_category):
    """Create and return a test Store owned by seller_user."""
    from stores.models import Store
    store, created = Store.objects.get_or_create(
        user=seller_user,
        defaults={
            'store_name': 'Toko Test Segar',
            'slug': 'toko-test-segar',
            'description': 'Toko testing untuk E2E dan unit test',
            'address': 'Jl. Test No. 1, Jakarta',
            'city': 'Jakarta',
            'category': test_category,
            'status': 'active',
        },
    )
    return store


@pytest.fixture
def seller_client(db, seller_user):
    """Provide an API client authenticated as seller_user (store owner)."""
    client = APIClient()
    client.force_authenticate(user=seller_user)
    return client


@pytest.fixture
def buyer_client(db, buyer_user):
    """Provide an API client authenticated as buyer_user (not store owner)."""
    client = APIClient()
    client.force_authenticate(user=buyer_user)
    return client
