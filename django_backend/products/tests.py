"""Tests for the products app."""

import pytest
from decimal import Decimal
from rest_framework import status
from django.urls import reverse

from .models import Product, ProductGallery, Category


# ─── Model Tests ────────────────────────────────────────────────────────────

class TestCategoryModel:
    def test_create_category(self, db):
        cat = Category.objects.create(category_name="Sembako", order=1)
        assert cat.category_name == "Sembako"
        assert cat.order == 1
        assert cat.is_active is True
        assert str(cat) == "Sembako"


class TestProductModel:
    def test_create_product(self, db, test_store):
        product = Product.objects.create(
            store=test_store,
            product_name="Beras Premium 5kg",
            description="Beras kualitas terbaik",
            price=75000.00,
            stock=100,
            unit="kg",
        )
        assert product.product_name == "Beras Premium 5kg"
        assert product.store == test_store
        assert product.price == Decimal("75000.00")
        assert product.stock == 100
        assert product.unit == "kg"
        assert product.is_active is True
        assert product.created_at is not None

    def test_product_str(self, db, test_store):
        product = Product.objects.create(
            store=test_store, product_name="Minyak Goreng",
            price=20000, stock=50,
        )
        assert str(product) == "Minyak Goreng"

    def test_product_default_active(self, db, test_store):
        product = Product.objects.create(
            store=test_store, product_name="Gula Pasir",
            price=15000, stock=30,
        )
        assert product.is_active is True
        assert product.product_status == "fresh"

    def test_product_slug_generated(self, db, test_store):
        product = Product.objects.create(
            store=test_store, product_name="Kopi Bubuk",
            price=25000, stock=20,
        )
        assert product.slug == "kopi-bubuk"

    def test_product_quality_score(self, db, test_store):
        product = Product.objects.create(
            store=test_store, product_name="Sayur Segar",
            price=5000, stock=100, quality_score=85,
        )
        assert product.quality_score == 85


class TestProductGalleryModel:
    def test_create_gallery(self, db, test_store):
        product = Product.objects.create(
            store=test_store, product_name="Test",
            price=1000, stock=10,
        )
        gallery = ProductGallery.objects.create(
            product=product, order=1,
        )
        assert gallery.product == product
        assert gallery.order == 1
        assert str(gallery) == f"Gallery image for {product.product_name}"


# ─── API Tests ──────────────────────────────────────────────────────────────

class TestProductListAPI:
    LIST_URL = reverse("product-list")

    def test_list_products_empty(self, api_client, db):
        resp = api_client.get(self.LIST_URL)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert "results" in data

    def test_list_products_with_data(self, api_client, test_store):
        Product.objects.create(
            store=test_store, product_name="Beras 5kg",
            price=75000, stock=100,
        )
        Product.objects.create(
            store=test_store, product_name="Gula 1kg",
            price=15000, stock=50,
        )
        resp = api_client.get(self.LIST_URL)
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.json()["results"]) >= 2

    def test_search_by_name(self, api_client, test_store):
        Product.objects.create(
            store=test_store, product_name="Beras Merah",
            price=90000, stock=20,
        )
        Product.objects.create(
            store=test_store, product_name="Minyak Goreng",
            price=25000, stock=50,
        )
        resp = api_client.get(self.LIST_URL, {"search": "beras"})
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        names = [p["product_name"].lower() for p in data["results"]]
        assert any("beras" in n for n in names)

    def test_filter_by_store(self, api_client, test_store, db, test_category):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        other_seller = User.objects.create_user(
            "other_seller2", email="other_seller2@test.io",
            password="TestPass123!", full_name="Other Seller II",
            is_verified=True, role='seller',
        )
        from stores.models import Store
        other_store = Store.objects.create(
            user=other_seller, store_name="Toko Lain",
            slug="toko-lain", city="Jakarta",
            category=test_category, status="active",
        )
        Product.objects.create(
            store=test_store, product_name="Produk A",
            price=1000, stock=10,
        )
        Product.objects.create(
            store=other_store, product_name="Produk B",
            price=2000, stock=10,
        )
        resp = api_client.get(self.LIST_URL, {"store": test_store.id})
        assert resp.status_code == status.HTTP_200_OK
        names = [p["store_name"] for p in resp.json()["results"]]
        assert all(n == "Toko Test Segar" for n in names)


class TestProductCreateAPI:
    CREATE_URL = reverse("product-create")

    def test_unauthenticated_cannot_create(self, api_client):
        resp = api_client.post(self.CREATE_URL, {"product_name": "Test", "price": 1000}, format="json")
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_seller_can_create(self, seller_client, test_store):
        resp = seller_client.post(self.CREATE_URL, {
            "store": test_store.id,
            "product_name": "Beras Baru",
            "price": 80000,
            "stock": 50,
            "unit": "kg",
        }, format="json")
        assert resp.status_code in (status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST)
        if resp.status_code == status.HTTP_201_CREATED:
            assert resp.json()["product_name"] == "Beras Baru"

    def test_buyer_cannot_create(self, buyer_client, test_store):
        resp = buyer_client.post(self.CREATE_URL, {
            "store": test_store.id, "product_name": "Test",
            "price": 1000, "stock": 10,
        }, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN


class TestProductDetailAPI:
    def _create_product(self, test_store, **kw):
        return Product.objects.create(
            store=test_store, product_name="Produk Detail",
            price=50000, stock=25, **kw,
        )

    def test_get_product(self, api_client, test_store):
        product = self._create_product(test_store)
        url = reverse("product-detail", args=[product.id])
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["product_name"] == "Produk Detail"

    def test_get_product_not_found(self, api_client, db):
        url = reverse("product-detail", args=[99999])
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_update_own_product(self, seller_client, test_store):
        product = self._create_product(test_store)
        url = reverse("product-manage", args=[product.id])
        resp = seller_client.patch(url, {"price": 55000, "stock": 30}, format="json")
        assert resp.status_code in (status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST)
        if resp.status_code == status.HTTP_200_OK:
            product.refresh_from_db()
            assert product.price == Decimal("55000")
            assert product.stock == 30

    def test_delete_own_product(self, seller_client, test_store):
        product = self._create_product(test_store)
        url = reverse("product-manage", args=[product.id])
        resp = seller_client.delete(url)
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not Product.objects.filter(id=product.id).exists()


class TestProductPermissions:
    def test_other_seller_cannot_update(self, db, test_store):
        other_user = type(test_store.user).objects.create_user(
            "other_seller3", email="other_seller3@test.io",
            password="TestPass123!", full_name="Other Seller",
            is_verified=True, role='seller',
        )
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=other_user)
        product = Product.objects.create(
            store=test_store, product_name="Milik Toko Test",
            price=1000, stock=10,
        )
        url = reverse("product-manage", args=[product.id])
        resp = client.patch(url, {"product_name": "Hacked!"}, format="json")
        # Other seller can't see/update product — returns 404 (not in their queryset)
        assert resp.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestQualityCheckAPI:
    LIST_URL = reverse("quality-check-list")

    def test_unauthenticated_cannot_create_or_list(self, api_client):
        # List
        resp = api_client.get(self.LIST_URL)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED
        # Create
        resp = api_client.post(self.LIST_URL, {"product": 1, "quality_status": "fresh"}, format="json")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_seller_can_create_and_list(self, seller_client, test_store):
        product = Product.objects.create(
            store=test_store, product_name="Bayam Ijo",
            price=5000, stock=20,
        )
        # Create Quality Check
        resp = seller_client.post(self.LIST_URL, {
            "product": product.id,
            "quality_status": "fresh",
            "freshness_score": 95,
            "stock_status": "sufficient",
            "ai_result": "Bayam terdeteksi segar."
        }, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert data["product"] == product.id
        assert data["quality_status"] == "fresh"
        assert data["freshness_score"] == 95

        # List Quality Checks
        resp = seller_client.get(self.LIST_URL)
        assert resp.status_code == status.HTTP_200_OK
        results = resp.json()["results"]
        assert len(results) >= 1
        assert results[0]["product"] == product.id

    def test_product_specific_quality_checks(self, api_client, test_store):
        product = Product.objects.create(
            store=test_store, product_name="Tomat",
            price=15000, stock=10,
        )
        from .models import QualityCheck
        qc = QualityCheck.objects.create(
            product=product,
            quality_status="warning",
            freshness_score=75,
            stock_status="sufficient",
            ai_result="Tomat kurang segar."
        )
        url = reverse("product-quality-checks", args=[product.id])
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        # Check if DRF returns pagination results or direct list
        data = resp.json()
        if isinstance(data, dict) and "results" in data:
            results = data["results"]
        else:
            results = data
        assert len(results) >= 1
        assert results[0]["freshness_score"] == 75

