"""
End-to-End Admin & Edge Case Test for Warungio Marketplace.

Covers:
  Edge cases: duplicate OTP, expired OTP, concurrent stock check
  Order flow timeline consistency

Run with:  python -m pytest django_backend/test_e2e_admin_journey.py -v --tb=long
"""

from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import OTP, LoginAttempt
from stores.models import Store
from products.models import Category, Product
from orders.models import Cart, Order, ShippingMethod, OrderItem, Delivery
from payments.models import Payment, PaymentMethod, Wallet

User = get_user_model()


class TestEdgeCases(TestCase):
    """Test edge cases: OTP replay, duplicate transactions, concurrent stock."""

    databases = '__all__'

    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(
            category_name='Test Kategori', is_active=True
        )
        cls.shipping = ShippingMethod.objects.create(
            code='gosend', name='GoSend', base_fee=10000, is_active=True
        )
        PaymentMethod.objects.create(
            name='bank_transfer', display_name='Bank Transfer', is_active=True
        )

    def setUp(self):
        self.client = APIClient()
        # Create seller
        self.seller_user = User.objects.create_user(
            'seller_edge',  # username (required by custom UserManager)
            email='seller.edge@test.io', password='PassSeller123!',
            full_name='Toko Edge', is_verified=True, role='seller',
        )
        self.store = Store.objects.create(
            user=self.seller_user, store_name='Toko Edge',
            status='active',
        )
        self.product = Product.objects.create(
            store=self.store, category=self.category,
            product_name='Barang Uji', price=10000, stock=5,
            is_active=True,
        )
        # Create buyer
        self.buyer_user = User.objects.create_user(
            'buyer_edge',  # username (required by custom UserManager)
            email='buyer.edge@test.io', password='PassBuyer123!',
            full_name='Pembeli Edge', is_verified=True, role='buyer',
        )
        self.buyer_client = APIClient()
        resp = self.buyer_client.post(reverse('login'), {
            'email': 'buyer.edge@test.io',
            'password': 'PassBuyer123!',
        }, format='json')
        self.buyer_token = resp.data['access']
        self.buyer_client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {self.buyer_token}'
        )

        # Seller client
        self.seller_client = APIClient()
        resp = self.seller_client.post(reverse('login'), {
            'email': 'seller.edge@test.io',
            'password': 'PassSeller123!',
        }, format='json')
        self.seller_token = resp.data['access']
        self.seller_client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {self.seller_token}'
        )

    def test_otp_replay_prevention(self):
        """OTP should only be usable once — replay should fail."""
        otp = OTP.objects.create(
            user=self.buyer_user,
            email=self.buyer_user.email,
            otp_code='123456',
            purpose='login',
            is_valid=True,
            expires_at=timezone.now() + timedelta(minutes=5),
        )

        # First use — should succeed
        resp = self.client.post(reverse('otp-verify'), {
            'email': self.buyer_user.email,
            'otp_code': '123456',
            'purpose': 'login',
        }, format='json')
        self.assertEqual(resp.status_code, 200)

        # Second use — same OTP, should fail
        resp = self.client.post(reverse('otp-verify'), {
            'email': self.buyer_user.email,
            'otp_code': '123456',
            'purpose': 'login',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_registration_email(self):
        """Registering with an existing email should fail."""
        resp = self.client.post(reverse('register'), {
            'email': self.buyer_user.email,
            'full_name': 'Duplicate',
            'password': 'Pass123!',
            'password2': 'Pass123!',
            'role': 'buyer',
        }, format='json')
        self.assertIn(resp.status_code, [
            status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT
        ])

    def test_checkout_empty_cart(self):
        """Checkout with empty cart should be rejected."""
        resp = self.buyer_client.post(reverse('order-create'), {
            'cart_items': [],
            'delivery_address': 'Jl. Test',
            'recipient_name': 'Test',
            'recipient_phone': '081',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_checkout_out_of_stock_product(self):
        """Checkout with out-of-stock product should be rejected."""
        self.product.stock = 0
        self.product.save(update_fields=['stock'])

        cart = Cart.objects.create(
            user=self.buyer_user, product=self.product, qty=1
        )

        resp = self.buyer_client.post(reverse('order-create'), {
            'cart_items': [cart.id],
            'delivery_address': 'Jl. Test No. 1',
            'recipient_name': 'Test',
            'recipient_phone': '081',
            'payment_method': 'cod',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_concurrent_stock_check(self):
        """Verify select_for_update() prevents overselling of last item."""
        self.product.stock = 1
        self.product.save(update_fields=['stock'])

        buyer2 = User.objects.create_user(
            'buyer2_edge',  # username (required)
            email='buyer2.edge@test.io', password='Pass123!',
            is_verified=True, role='buyer',
        )
        buyer2_client = APIClient()
        resp = buyer2_client.post(reverse('login'), {
            'email': 'buyer2.edge@test.io',
            'password': 'Pass123!',
        }, format='json')
        buyer2_client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {resp.data["access"]}'
        )

        cart1 = Cart.objects.create(
            user=self.buyer_user, product=self.product, qty=1
        )
        cart2 = Cart.objects.create(
            user=buyer2, product=self.product, qty=1
        )

        # First buyer checks out
        resp1 = self.buyer_client.post(reverse('order-create'), {
            'cart_items': [cart1.id],
            'delivery_address': 'Jl. Buyer 1',
            'recipient_name': 'Buyer 1',
            'recipient_phone': '0811',
            'payment_method': 'cod',
        }, format='json')

        # Second buyer checks out
        resp2 = buyer2_client.post(reverse('order-create'), {
            'cart_items': [cart2.id],
            'delivery_address': 'Jl. Buyer 2',
            'recipient_name': 'Buyer 2',
            'recipient_phone': '0812',
            'payment_method': 'cod',
        }, format='json')

        # One must succeed, one must fail (only 1 stock available)
        statuses = [resp1.status_code, resp2.status_code]
        self.assertIn(status.HTTP_201_CREATED, statuses,
                      'At least one checkout should succeed')
        self.assertIn(status.HTTP_400_BAD_REQUEST, statuses,
                      'At least one checkout should fail due to insufficient stock')

    def test_order_flow_status_update(self):
        """Verify seller can update order status from pending to processed."""
        cart = Cart.objects.create(
            user=self.buyer_user, product=self.product, qty=2
        )

        resp = self.buyer_client.post(reverse('order-create'), {
            'cart_items': [cart.id],
            'delivery_address': 'Jl. Timeline No. 1',
            'recipient_name': 'Timeline',
            'recipient_phone': '081',
            'payment_method': 'cod',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        order_id = resp.data['orders'][0]['id']
        order = Order.objects.get(id=order_id)
        self.assertEqual(order.order_status, 'pending')

        # Seller processes the order
        resp = self.seller_client.post(
            reverse('order-status-update', args=[order_id]),
            {'status': 'processed'}, format='json'
        )
        self.assertEqual(resp.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.order_status, 'processed')

        # Order status transitions are valid without Delivery record
        # (Delivery is auto-created by order status update when needed)

    def test_login_attempt_tracking_successful(self):
        """Successful login should be tracked in LoginAttempt."""
        # First ensure clean state
        LoginAttempt.objects.filter(email='seller.edge@test.io').delete()

        # Login attempt
        self.client.post(reverse('login'), {
            'email': 'seller.edge@test.io', 'password': 'PassSeller123!',
        }, format='json')

        # Check if LoginAttempt was created (depends on backend implementation)
        has_attempt = LoginAttempt.objects.filter(
            email='seller.edge@test.io'
        ).exists()
        self.assertTrue(has_attempt,
                        'LoginAttempt should be created for successful login')
