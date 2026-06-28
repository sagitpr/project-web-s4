"""Tests for the payments app."""

import pytest
from rest_framework import status
from django.urls import reverse

from .models import Payment, PaymentMethod, MidtransTransaction
from orders.models import Order


class TestPaymentMethodModel:
    """Test PaymentMethod model."""

    def test_create_payment_method(self, db):
        pm = PaymentMethod.objects.create(
            name="bank_transfer",
            display_name="Bank Transfer",
            is_active=True,
        )
        assert pm.name == "bank_transfer"
        assert pm.display_name == "Bank Transfer"
        assert pm.is_active is True
        assert str(pm) == "Bank Transfer"


class TestPaymentModel:
    """Test Payment model creation, status choices, and defaults."""

    def test_create_payment(self, db, test_store, buyer_user):
        order = Order.objects.create(
            user=buyer_user, store=test_store, total_price=100000,
        )
        payment = Payment.objects.create(
            order=order,
            user=buyer_user,
            amount=100000,
            payment_type="bank_transfer",
            payment_status="pending",
        )
        assert payment.order == order
        assert payment.user == buyer_user
        assert payment.amount == 100000
        assert payment.payment_type == "bank_transfer"
        assert payment.payment_status == "pending"
        assert payment.transaction_code.startswith("PAY-")
        assert payment.created_at is not None

    def test_payment_str(self, db, test_store, buyer_user):
        order = Order.objects.create(
            user=buyer_user, store=test_store, total_price=50000,
        )
        payment = Payment.objects.create(
            order=order, user=buyer_user, amount=50000, payment_type="cod",
        )
        assert str(payment) == f"Payment {payment.transaction_code} - pending"

    def test_payment_status_choices(self, db, test_store, buyer_user):
        order = Order.objects.create(
            user=buyer_user, store=test_store, total_price=25000,
        )
        for status_val in ["pending", "paid", "failed", "refunded", "expired"]:
            payment = Payment.objects.create(
                order=order, user=buyer_user,
                amount=25000, payment_type="cod",
                payment_status=status_val,
            )
            assert payment.payment_status == status_val

    def test_payment_default_status(self, db, test_store, buyer_user):
        order = Order.objects.create(
            user=buyer_user, store=test_store, total_price=10000,
        )
        payment = Payment.objects.create(
            order=order, user=buyer_user, amount=10000, payment_type="qris",
        )
        assert payment.payment_status == "pending"

    def test_payment_net_amount(self, db, test_store, buyer_user):
        order = Order.objects.create(
            user=buyer_user, store=test_store, total_price=50000,
        )
        payment = Payment.objects.create(
            order=order, user=buyer_user,
            amount=50000, fee=2500, payment_type="bank_transfer",
        )
        assert payment.net_amount == 47500


class TestMidtransTransactionModel:
    """Test MidtransTransaction model."""

    def test_create_midtrans_tx(self, db, test_store, buyer_user):
        order = Order.objects.create(
            user=buyer_user, store=test_store, total_price=100000,
        )
        payment = Payment.objects.create(
            order=order, user=buyer_user, amount=100000, payment_type="bank_transfer",
        )
        tx = MidtransTransaction.objects.create(
            payment=payment,
            order_id="WRG-TEST-001",
            transaction_status="pending",
        )
        assert tx.payment == payment
        assert tx.order_id == "WRG-TEST-001"
        assert tx.transaction_status == "pending"
        assert str(tx) == "Midtrans WRG-TEST-001 - pending"


# ─── API Tests ──────────────────────────────────────────────────────────────

class TestPaymentMethodListAPI:
    URL = reverse("payment-methods")

    def test_list_methods(self, api_client, db):
        resp = api_client.get(self.URL)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        # May be paginated (dict with results) or flat list
        if isinstance(data, dict):
            assert "results" in data
        else:
            assert isinstance(data, list)

    def test_list_methods_with_data(self, api_client, db):
        PaymentMethod.objects.create(name="cod", display_name="COD", is_active=True)
        PaymentMethod.objects.create(name="qris", display_name="QRIS", is_active=True)
        resp = api_client.get(self.URL)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        if isinstance(data, dict):
            assert len(data["results"]) >= 2
        else:
            assert len(data) >= 2


class TestPaymentHistoryAPI:
    URL = reverse("payment-history")

    def test_history_requires_auth(self, api_client):
        resp = api_client.get(self.URL)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_history_returns_data(self, authed_client, verified_user, test_store):
        order = Order.objects.create(
            user=verified_user, store=test_store, total_price=30000,
        )
        Payment.objects.create(
            order=order, user=verified_user, amount=30000, payment_type="cod",
        )
        resp = authed_client.get(self.URL)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        # May be paginated (dict with results) or flat list
        if isinstance(data, dict):
            assert "results" in data
        else:
            assert isinstance(data, list)


class TestPaymentStatusAPI:
    def test_payment_status(self, authed_client, verified_user, test_store):
        order = Order.objects.create(
            user=verified_user, store=test_store, total_price=75000,
        )
        Payment.objects.create(
            order=order, user=verified_user, amount=75000, payment_type="bank_transfer",
        )
        url = reverse("payment-status", args=[order.id])
        resp = authed_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert "payment_status" in data

    def test_payment_status_other_user(self, db, test_store, verified_user, buyer_user):
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=buyer_user)
        order = Order.objects.create(
            user=verified_user, store=test_store, total_price=60000,
        )
        Payment.objects.create(
            order=order, user=verified_user, amount=60000, payment_type="cod",
        )
        url = reverse("payment-status", args=[order.id])
        resp = client.get(url)
        # Should return no_payment or 404 since it filters by request.user
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json().get("status") == "no_payment"
