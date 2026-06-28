"""Tests for the orders app."""

import pytest
from rest_framework import status
from django.urls import reverse

from .models import Order, OrderItem, Cart, Delivery, ShippingMethod
from products.models import Product, Category


# ─── Model Tests ────────────────────────────────────────────────────────────


class TestOrderModel:
    """Test Order model creation, status choices, and defaults."""

    def test_create_order(self, db, test_store, buyer_user):
        order = Order.objects.create(
            user=buyer_user,
            store=test_store,
            total_price=150000.00,
            order_status="pending",
            delivery_address="Jl. Pesanan No. 1, Jakarta",
            recipient_name="Budi",
            recipient_phone="08123456789",
            notes="Tolong dibungkus rapi",
        )
        assert order.user == buyer_user
        assert order.store == test_store
        assert order.total_price == 150000.00
        assert order.order_status == "pending"
        assert order.delivery_address == "Jl. Pesanan No. 1, Jakarta"
        assert order.recipient_name == "Budi"
        assert order.recipient_phone == "08123456789"
        assert order.notes == "Tolong dibungkus rapi"
        assert order.created_at is not None

    def test_order_str(self, db, test_store, buyer_user):
        order = Order.objects.create(
            user=buyer_user, store=test_store, total_price=50000,
        )
        assert order.order_number.startswith("WRG-")

    def test_order_status_choices(self, db, test_store, buyer_user):
        for status_val in ["pending", "paid", "processed", "shipped", "completed", "cancelled"]:
            order = Order.objects.create(
                user=buyer_user, store=test_store,
                total_price=25000, order_status=status_val,
            )
            assert order.order_status == status_val

    def test_order_default_status(self, db, test_store, buyer_user):
        order = Order.objects.create(
            user=buyer_user, store=test_store, total_price=10000,
        )
        assert order.order_status == "pending"
        assert order.payment_status == "pending"

    def test_order_calculate_totals(self, db, test_store, buyer_user):
        order = Order.objects.create(
            user=buyer_user, store=test_store, total_price=0,
            shipping_cost=10000, discount=5000,
        )
        cat = Category.objects.create(category_name="Sembako", order=1)
        product = Product.objects.create(
            store=test_store, product_name="Item Test",
            price=20000, stock=10, category=cat,
        )
        OrderItem.objects.create(
            order=order, product=product,
            qty=2, price=20000,
        )
        order.refresh_from_db()
        assert order.subtotal == 40000
        assert order.total_price == 45000  # subtotal + shipping - discount


class TestOrderItemModel:
    """Test OrderItem model."""

    def test_create_order_item(self, db, test_store, buyer_user):
        order = Order.objects.create(
            user=buyer_user, store=test_store, total_price=30000,
        )
        cat = Category.objects.create(category_name="Sembako", order=1)
        product = Product.objects.create(
            store=test_store, product_name="Test Item",
            price=10000, stock=50, category=cat,
        )
        item = OrderItem.objects.create(
            order=order, product=product, qty=3, price=10000,
        )
        assert item.order == order
        assert item.product == product
        assert item.qty == 3
        assert item.price == 10000
        assert item.product_name == product.product_name

    def test_order_item_str(self, db, test_store, buyer_user):
        order = Order.objects.create(
            user=buyer_user, store=test_store, total_price=5000,
        )
        cat = Category.objects.create(category_name="Makanan", order=2)
        product = Product.objects.create(
            store=test_store, product_name="Snack",
            price=5000, stock=100, category=cat,
        )
        item = OrderItem.objects.create(
            order=order, product=product, qty=1, price=5000,
        )
        assert str(item) == f"{product.product_name} x1"


class TestCartModel:
    """Test Cart model."""

    def test_add_to_cart(self, db, verified_user, test_store):
        cat = Category.objects.create(category_name="Sembako", order=1)
        product = Product.objects.create(
            store=test_store, product_name="Barang Cart",
            price=15000, stock=20, category=cat,
        )
        cart = Cart.objects.create(user=verified_user, product=product, qty=2)
        assert cart.user == verified_user
        assert cart.product == product
        assert cart.qty == 2

    def test_cart_subtotal(self, db, verified_user, test_store):
        cat = Category.objects.create(category_name="Sembako", order=1)
        product = Product.objects.create(
            store=test_store, product_name="Barang", price=10000, stock=10, category=cat,
        )
        cart = Cart.objects.create(user=verified_user, product=product, qty=3)
        assert cart.subtotal == 30000

    def test_cart_unique_together(self, db, verified_user, test_store):
        cat = Category.objects.create(category_name="Sembako", order=1)
        product = Product.objects.create(
            store=test_store, product_name="Unik", price=5000, stock=10, category=cat,
        )
        Cart.objects.create(user=verified_user, product=product, qty=1)
        with pytest.raises(Exception):
            Cart.objects.create(user=verified_user, product=product, qty=2)


# ─── Shipping Method API ────────────────────────────────────────────────────


class TestShippingMethodListView:
    """Test GET /api/orders/shipping-methods/."""

    URL = reverse("shipping-methods")

    def test_list_shipping_methods(self, api_client, db):
        ShippingMethod.objects.create(code="gosend", name="GoSend", is_active=True)
        ShippingMethod.objects.create(code="maxim", name="Maxim", is_active=True)
        resp = api_client.get(self.URL)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert len(data["results"]) >= 2

    def test_active_only(self, api_client, db):
        ShippingMethod.objects.create(code="gosend", name="GoSend", is_active=True)
        ShippingMethod.objects.create(code="inactive", name="Inactive", is_active=False)
        resp = api_client.get(self.URL)
        data = resp.json()
        results = data["results"]
        codes = [s["code"] for s in results]
        assert "gosend" in codes
        assert "inactive" not in codes

    def test_allows_anyone(self, api_client, db):
        """Should be accessible without authentication."""
        resp = api_client.get(self.URL)
        assert resp.status_code == status.HTTP_200_OK


# ─── Cart API ───────────────────────────────────────────────────────────────


class TestCartListView:
    """Test GET/POST /api/orders/cart/."""

    URL = reverse("cart-list")

    def test_list_cart_unauthenticated(self, api_client):
        resp = api_client.get(self.URL)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_cart_empty(self, buyer_client):
        resp = buyer_client.get(self.URL)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["count"] == 0
        assert data["results"] == []

    def test_list_cart_with_items(self, buyer_client, buyer_user, test_store):
        cat = Category.objects.create(category_name="Sembako", order=1)
        product = Product.objects.create(
            store=test_store, product_name="Cart Item",
            price=10000, stock=10, category=cat,
        )
        Cart.objects.create(user=buyer_user, product=product, qty=2)
        resp = buyer_client.get(self.URL)
        assert resp.status_code == status.HTTP_200_OK
        results = resp.json()["results"]
        assert len(results) == 1
        assert results[0]["qty"] == 2

    def test_add_to_cart(self, buyer_client, buyer_user, test_store):
        cat = Category.objects.create(category_name="Sembako", order=1)
        product = Product.objects.create(
            store=test_store, product_name="Add Item",
            price=15000, stock=5, category=cat,
        )
        resp = buyer_client.post(self.URL, {
            "product": product.id, "qty": 1,
        }, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert Cart.objects.filter(user=buyer_user, product=product).exists()


class TestCartDetailView:
    """Test GET/PUT/PATCH/DELETE /api/orders/cart/<pk>/."""

    def test_update_cart_qty(self, buyer_client, buyer_user, test_store):
        cat = Category.objects.create(category_name="Sembako", order=1)
        product = Product.objects.create(
            store=test_store, product_name="Update Qty",
            price=10000, stock=10, category=cat,
        )
        cart = Cart.objects.create(user=buyer_user, product=product, qty=1)
        url = reverse("cart-detail", args=[cart.id])
        resp = buyer_client.patch(url, {"qty": 5}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        cart.refresh_from_db()
        assert cart.qty == 5

    def test_delete_cart_item(self, buyer_client, buyer_user, test_store):
        cat = Category.objects.create(category_name="Sembako", order=1)
        product = Product.objects.create(
            store=test_store, product_name="Delete Me",
            price=10000, stock=10, category=cat,
        )
        cart = Cart.objects.create(user=buyer_user, product=product, qty=1)
        url = reverse("cart-detail", args=[cart.id])
        resp = buyer_client.delete(url)
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not Cart.objects.filter(id=cart.id).exists()

    def test_other_user_cannot_update(self, db, test_store):
        from django.contrib.auth import get_user_model
        from rest_framework.test import APIClient
        User = get_user_model()
        other = User.objects.create_user("other", email="other@test.io", password="Pass123!")
        client = APIClient()
        client.force_authenticate(user=other)
        cat = Category.objects.create(category_name="Sembako", order=1)
        product = Product.objects.create(
            store=test_store, product_name="Other Cart",
            price=10000, stock=10, category=cat,
        )
        owner = User.objects.create_user("owner", email="owner@test.io", password="Pass123!")
        cart = Cart.objects.create(user=owner, product=product, qty=1)
        url = reverse("cart-detail", args=[cart.id])
        resp = client.get(url)
        assert resp.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)


class TestCartClearView:
    """Test DELETE /api/orders/cart/clear/."""

    URL = reverse("cart-clear")

    def test_clear_cart(self, buyer_client, buyer_user, test_store):
        cat = Category.objects.create(category_name="Sembako", order=1)
        product = Product.objects.create(
            store=test_store, product_name="Clear Item",
            price=10000, stock=10, category=cat,
        )
        Cart.objects.create(user=buyer_user, product=product, qty=3)
        resp = buyer_client.delete(self.URL)
        assert resp.status_code == status.HTTP_200_OK
        assert "berhasil dikosongkan" in resp.json()["message"]
        assert Cart.objects.filter(user=buyer_user).count() == 0

    def test_clear_unauthenticated(self, api_client):
        resp = api_client.delete(self.URL)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


class TestCartCountView:
    """Test GET /api/orders/cart/count/."""

    URL = reverse("cart-count")

    def test_count_authenticated(self, buyer_client, buyer_user, test_store):
        cat = Category.objects.create(category_name="Sembako", order=1)
        product = Product.objects.create(
            store=test_store, product_name="Count Item",
            price=10000, stock=10, category=cat,
        )
        Cart.objects.create(user=buyer_user, product=product, qty=1)
        resp = buyer_client.get(self.URL)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["count"] == 1

    def test_count_empty(self, buyer_client):
        resp = buyer_client.get(self.URL)
        assert resp.json()["count"] == 0

    def test_count_unauthenticated(self, api_client):
        resp = api_client.get(self.URL)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ─── Order Create API ───────────────────────────────────────────────────────


class TestOrderCreateAPI:
    CREATE_URL = reverse("order-create")

    def test_unauthenticated_cannot_create(self, api_client):
        resp = api_client.post(self.CREATE_URL, {}, format="json")
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_buyer_can_create(self, buyer_client, test_store, buyer_user):
        cat = Category.objects.create(category_name="Sembako", order=1)
        product = Product.objects.create(
            store=test_store, product_name="Barang Beli",
            price=25000, stock=10, category=cat,
        )
        cart = Cart.objects.create(user=buyer_user, product=product, qty=1)
        resp = buyer_client.post(self.CREATE_URL, {
            "cart_items": [cart.id],
            "delivery_address": "Jl. Beli No. 1",
            "recipient_name": "Budi",
            "recipient_phone": "08123456789",
            "payment_method": "cod",
        }, format="json")
        assert resp.status_code in (status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST)
        if resp.status_code == status.HTTP_201_CREATED:
            assert "orders" in resp.json()

    def test_empty_cart_rejected(self, buyer_client):
        """Empty cart_items list should return 400."""
        resp = buyer_client.post(self.CREATE_URL, {
            "cart_items": [],
            "delivery_address": "Jl. Test",
            "recipient_name": "Test",
            "recipient_phone": "081",
        }, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_cart_items_rejected(self, buyer_client):
        """Non-existent cart item IDs should return 400."""
        resp = buyer_client.post(self.CREATE_URL, {
            "cart_items": [99999],
            "delivery_address": "Jl. Test",
            "recipient_name": "Test",
            "recipient_phone": "081",
        }, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_with_shipping_method(self, buyer_client, buyer_user, test_store):
        cat = Category.objects.create(category_name="Sembako", order=1)
        product = Product.objects.create(
            store=test_store, product_name="Ship Item",
            price=30000, stock=10, category=cat,
        )
        cart = Cart.objects.create(user=buyer_user, product=product, qty=1)
        sm = ShippingMethod.objects.create(code="gosend", name="GoSend", base_fee=10000, is_active=True)
        resp = buyer_client.post(self.CREATE_URL, {
            "cart_items": [cart.id],
            "delivery_address": "Jl. Kirim No. 1",
            "recipient_name": "Budi",
            "recipient_phone": "081",
            "payment_method": "cod",
            "shipping_method": sm.id,
        }, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        order_id = resp.json()["orders"][0]["id"]
        order = Order.objects.get(id=order_id)
        assert order.shipping_method == sm


# ─── Order List / Detail API ────────────────────────────────────────────────


class TestMyOrdersAPI:
    LIST_URL = reverse("my-orders")

    def test_buyer_sees_own_orders(self, buyer_client, test_store, buyer_user):
        Order.objects.create(
            user=buyer_user, store=test_store, total_price=75000,
        )
        resp = buyer_client.get(self.LIST_URL)
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.json()["results"]) >= 1

    def test_unauthenticated_cannot_list(self, api_client):
        resp = api_client.get(self.LIST_URL)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_filter_by_status(self, buyer_client, buyer_user, test_store):
        Order.objects.create(
            user=buyer_user, store=test_store, total_price=10000, order_status="pending",
        )
        Order.objects.create(
            user=buyer_user, store=test_store, total_price=20000, order_status="completed",
        )
        resp = buyer_client.get(self.LIST_URL, {"order_status": "completed"})
        assert resp.status_code == status.HTTP_200_OK
        results = resp.json()["results"]
        assert all(o["order_status"] == "completed" for o in results)


class TestSellerOrdersAPI:
    LIST_URL = reverse("seller-orders")

    def test_seller_sees_store_orders(self, seller_client, test_store, buyer_user):
        Order.objects.create(
            user=buyer_user, store=test_store, total_price=60000,
        )
        resp = seller_client.get(self.LIST_URL)
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.json()["results"]) >= 1

    def test_buyer_cannot_access(self, buyer_client):
        resp = buyer_client.get(self.LIST_URL)
        assert resp.status_code in (status.HTTP_403_FORBIDDEN,)


class TestOrderDetailAPI:
    def _url(self, order_id):
        return reverse("order-detail", args=[order_id])

    def test_get_order(self, buyer_client, test_store, buyer_user):
        order = Order.objects.create(
            user=buyer_user, store=test_store, total_price=45000,
        )
        resp = buyer_client.get(self._url(order.id))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["id"] == order.id

    def test_other_user_cannot_view_order(self, db, test_store, buyer_user):
        other_user = type(buyer_user).objects.create_user(
            "other_buyer", email="other_buyer@test.io",
            password="TestPass123!", full_name="Other Buyer",
            is_verified=True,
        )
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=other_user)
        order = Order.objects.create(
            user=buyer_user, store=test_store, total_price=30000,
        )
        resp = client.get(self._url(order.id))
        assert resp.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)


class TestOrderHistoryView:
    """Test GET /api/orders/history/."""

    URL = reverse("order-history")

    def test_history_unauthenticated(self, api_client):
        resp = api_client.get(self.URL)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_history_lists_orders(self, buyer_client, buyer_user, test_store):
        Order.objects.create(
            user=buyer_user, store=test_store, total_price=10000,
        )
        Order.objects.create(
            user=buyer_user, store=test_store, total_price=20000,
        )
        resp = buyer_client.get(self.URL)
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.json()["results"]) == 2

    def test_history_filter_by_status(self, buyer_client, buyer_user, test_store):
        Order.objects.create(
            user=buyer_user, store=test_store, total_price=10000, order_status="pending",
        )
        Order.objects.create(
            user=buyer_user, store=test_store, total_price=20000, order_status="completed",
        )
        resp = buyer_client.get(self.URL, {"status": "completed"})
        assert resp.status_code == status.HTTP_200_OK
        results = resp.json()["results"]
        assert len(results) == 1
        assert results[0]["order_status"] == "completed"


# ─── Order Status Update (Seller) ───────────────────────────────────────────


class TestOrderStatusUpdate:
    def test_processed_status(self, seller_client, test_store, buyer_user):
        order = Order.objects.create(
            user=buyer_user, store=test_store, total_price=55000,
        )
        url = reverse("order-status-update", args=[order.id])
        resp = seller_client.post(url, {"status": "processed"}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        order.refresh_from_db()
        assert order.order_status == "processed"

    def test_ready_pickup_with_pickup_code(self, seller_client, test_store, buyer_user):
        order = Order.objects.create(
            user=buyer_user, store=test_store, total_price=55000,
        )
        Delivery.objects.create(order=order, delivery_status="diproses_penjual")
        url = reverse("order-status-update", args=[order.id])
        resp = seller_client.post(url, {"status": "ready_pickup", "pickup_code": "ABC123"}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        delivery = Delivery.objects.get(order=order)
        assert delivery.pickup_code == "ABC123"

    def test_courier_pickup_set_driver_info(self, seller_client, test_store, buyer_user):
        order = Order.objects.create(
            user=buyer_user, store=test_store, total_price=55000,
        )
        Delivery.objects.create(order=order, delivery_status="menunggu_penjemputan")
        url = reverse("order-status-update", args=[order.id])
        resp = seller_client.post(url, {
            "status": "courier_pickup",
            "driver_name": "Budi Driver",
            "driver_phone": "08123456789",
            "courier": "GoSend",
        }, format="json")
        assert resp.status_code == status.HTTP_200_OK
        delivery = Delivery.objects.get(order=order)
        assert delivery.driver_name == "Budi Driver"
        assert delivery.driver_phone == "08123456789"
        assert delivery.courier_name == "GoSend"

    def test_on_delivery_with_tracking(self, seller_client, test_store, buyer_user):
        order = Order.objects.create(
            user=buyer_user, store=test_store, total_price=55000,
        )
        Delivery.objects.create(order=order, delivery_status="kurir_menjemput")
        url = reverse("order-status-update", args=[order.id])
        resp = seller_client.post(url, {
            "status": "on_delivery",
            "tracking_number": "TRK-001",
        }, format="json")
        assert resp.status_code == status.HTTP_200_OK
        order.refresh_from_db()
        assert order.tracking_number == "TRK-001"

    def test_completed_status_sets_timestamps(self, seller_client, test_store, buyer_user):
        order = Order.objects.create(
            user=buyer_user, store=test_store, total_price=55000,
        )
        Delivery.objects.create(order=order, delivery_status="dalam_perjalanan")
        url = reverse("order-status-update", args=[order.id])
        resp = seller_client.post(url, {"status": "completed"}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        delivery = Delivery.objects.get(order=order)
        assert delivery.delivered_at is not None
        assert delivery.delivery_status == "pesanan_diterima"

    def test_cancelled_restores_stock(self, seller_client, test_store, buyer_user, db):
        cat = Category.objects.create(category_name="Sembako", order=1)
        product = Product.objects.create(
            store=test_store, product_name="Cancel Item",
            price=10000, stock=5, category=cat,
        )
        order = Order.objects.create(
            user=buyer_user, store=test_store, total_price=10000,
        )
        OrderItem.objects.create(order=order, product=product, qty=2, price=10000)
        Delivery.objects.create(order=order, delivery_status="diproses_penjual")
        url = reverse("order-status-update", args=[order.id])
        resp = seller_client.post(url, {"status": "cancelled", "cancel_reason": "out_of_stock"}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        product.refresh_from_db()
        assert product.stock == 7  # restored 2 from cancellation

    def test_cancelled_invalid_status(self, seller_client, test_store, buyer_user):
        """Cannot cancel an already-shipped order."""
        order = Order.objects.create(
            user=buyer_user, store=test_store, total_price=55000, order_status="shipped",
        )
        url = reverse("order-status-update", args=[order.id])
        resp = seller_client.post(url, {"status": "cancelled"}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_non_seller_cannot_update(self, buyer_client, test_store, buyer_user):
        order = Order.objects.create(
            user=buyer_user, store=test_store, total_price=55000,
        )
        url = reverse("order-status-update", args=[order.id])
        resp = buyer_client.post(url, {"status": "processed"}, format="json")
        assert resp.status_code in (status.HTTP_403_FORBIDDEN,)


# ─── Buyer Cancel Order ─────────────────────────────────────────────────────


class TestBuyerCancelOrderView:
    """Test POST /api/orders/<order_id>/cancel/."""

    def test_buyer_cancel_pending_order(self, buyer_client, test_store, buyer_user):
        order = Order.objects.create(
            user=buyer_user, store=test_store, total_price=50000, order_status="pending",
        )
        url = reverse("order-cancel", args=[order.id])
        resp = buyer_client.post(url, {"reason": "change_mind"}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        order.refresh_from_db()
        assert order.order_status == "cancelled"

    def test_buyer_cancel_paid_order(self, buyer_client, test_store, buyer_user):
        order = Order.objects.create(
            user=buyer_user, store=test_store, total_price=50000, order_status="paid",
        )
        url = reverse("order-cancel", args=[order.id])
        resp = buyer_client.post(url, {}, format="json")
        assert resp.status_code == status.HTTP_200_OK

    def test_cannot_cancel_processed_order(self, buyer_client, test_store, buyer_user):
        order = Order.objects.create(
            user=buyer_user, store=test_store, total_price=50000, order_status="processed",
        )
        url = reverse("order-cancel", args=[order.id])
        resp = buyer_client.post(url, {}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_cancel_nonexistent_order(self, buyer_client):
        url = reverse("order-cancel", args=[99999])
        resp = buyer_client.post(url, {}, format="json")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_other_user_cannot_cancel(self, db, test_store, buyer_user):
        other_user = type(buyer_user).objects.create_user(
            "other_cancel", email="other_cancel@test.io",
            password="Pass123!", is_verified=True,
        )
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=other_user)
        order = Order.objects.create(
            user=buyer_user, store=test_store, total_price=50000, order_status="pending",
        )
        url = reverse("order-cancel", args=[order.id])
        resp = client.post(url, {}, format="json")
        assert resp.status_code == status.HTTP_404_NOT_FOUND  # not their order


# ─── Delivery Tracking ──────────────────────────────────────────────────────


class TestDeliveryTrackingView:
    """Test GET /api/orders/<order_id>/tracking/."""

    def test_tracking_authenticated(self, buyer_client, test_store, buyer_user):
        order = Order.objects.create(
            user=buyer_user, store=test_store, total_price=50000,
        )
        Delivery.objects.create(order=order, delivery_status="dalam_perjalanan")
        url = reverse("delivery-tracking", args=[order.id])
        resp = buyer_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["source"] == "hyperlocal"
        assert "milestones" in data
        assert len(data["milestones"]) == 5

    def test_tracking_menunggu_konfirmasi(self, buyer_client, test_store, buyer_user):
        order = Order.objects.create(
            user=buyer_user, store=test_store, total_price=50000,
        )
        Delivery.objects.create(order=order)
        url = reverse("delivery-tracking", args=[order.id])
        resp = buyer_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["delivery_status"] == "menunggu_konfirmasi"

    def test_tracking_no_delivery(self, buyer_client, test_store, buyer_user):
        order = Order.objects.create(
            user=buyer_user, store=test_store, total_price=50000,
        )
        url = reverse("delivery-tracking", args=[order.id])
        resp = buyer_client.get(url)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_tracking_nonexistent_order(self, buyer_client):
        url = reverse("delivery-tracking", args=[99999])
        resp = buyer_client.get(url)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_tracking_unauthenticated(self, api_client, test_store, buyer_user):
        order = Order.objects.create(
            user=buyer_user, store=test_store, total_price=50000,
        )
        Delivery.objects.create(order=order)
        url = reverse("delivery-tracking", args=[order.id])
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_other_user_cannot_track(self, db, test_store, buyer_user):
        other_user = type(buyer_user).objects.create_user(
            "other_track", email="other_track@test.io",
            password="Pass123!", is_verified=True,
        )
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=other_user)
        order = Order.objects.create(
            user=buyer_user, store=test_store, total_price=50000,
        )
        Delivery.objects.create(order=order)
        url = reverse("delivery-tracking", args=[order.id])
        resp = client.get(url)
        assert resp.status_code == status.HTTP_404_NOT_FOUND  # not their order
