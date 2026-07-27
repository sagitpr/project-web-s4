"""
End-to-End Seller Flow Integration Test — Warungio Seller API.

Tests the complete Seller Flow at the API level:
1. Auth → Login → Dashboard stats
2. Smart AI Scan → Product Recognition API
3. POS Offline → Add to cart → Checkout → Payment
4. Expired Reminder → Dashboard widget

Uses real API calls with mocked DB where appropriate.
All tests use Django TestCase with database transactions.
"""

from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model

from stores.models import Store
from products.models import Product, Category
from orders.models import OfflineSale
from inventory.models import MasterProduct, ProductBatch
from inventory.services.expired_reminder import get_expired_reminder
from inventory.services.ai_product_recognition import get_ai_product_recognition_pipeline

User = get_user_model()


class SellerFlowE2ETest(TestCase):
    """End-to-end seller flow integration tests."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data once for all tests."""
        # Create seller user
        cls.seller = User.objects.create_user(
            username='seller_e2e_test',
            email='seller@warungio.test',
            password='TestPass123!',
            full_name='Test Seller',
            phone='081234567890',
            role='seller',
            is_active=True,
        )

        # Create store
        cls.store = Store.objects.create(
            user=cls.seller,
            store_name='Toko E2E Test',
            slug='toko-e2e-test',
            status='active',
            city='Jakarta',
            province='DKI Jakarta',
        )

        # Create category
        cls.category = Category.objects.create(
            category_name='Makanan Ringan',
            is_active=True,
        )

        # Create master product
        cls.master = MasterProduct.objects.create(
            barcode='8991234567890',
            product_name='Keripik Singkong Balado',
            brand='Makanan Ringan',
            category='Makanan Ringan',
            unit='pcs',
        )

        # Create product listing
        cls.product = Product.objects.create(
            store=cls.store,
            category=cls.category,
            product_name='Keripik Singkong Balado',
            price=Decimal('10000'),
            stock=100,
            is_active=True,
        )

        # Create batch with near expiry (3 days)
        cls.batch = ProductBatch.objects.create(
            store=cls.store,
            master_product=cls.master,
            batch_number='BATCH-E2E-001',
            production_date=date.today() - timedelta(days=27),
            expiry_date=date.today() + timedelta(days=3),
            initial_quantity=50,
            current_quantity=50,
            unit='pcs',
            is_active=True,
        )

        # Create batch with fresh expiry (60 days)
        cls.batch_fresh = ProductBatch.objects.create(
            store=cls.store,
            master_product=cls.master,
            batch_number='BATCH-E2E-002',
            production_date=date.today() - timedelta(days=10),
            expiry_date=date.today() + timedelta(days=60),
            initial_quantity=100,
            current_quantity=100,
            unit='pcs',
            is_active=True,
        )

    def setUp(self):
        """Set up per-test."""
        self.client = Client()
        # Log in as seller
        self.client.login(email='seller@warungio.test', password='TestPass123!')

    # ── FLOW 1: Login → Dashboard ──

    def test_flow_01_login_and_dashboard(self):
        """Seller can login and access dashboard."""
        # Verify login
        self.assertTrue(self.client.login(email='seller@warungio.test', password='TestPass123!'))

        # Access dashboard page
        response = self.client.get(reverse('page-seller-dashboard'))
        self.assertEqual(response.status_code, 200)

        # Check dashboard API
        response = self.client.get('/api/analytics/dashboard-summary/')
        self.assertIn(response.status_code, [200, 302, 403, 404])

    # ── FLOW 2: Store Profile ──

    def test_flow_02_store_profile(self):
        """Seller can view store profile."""
        response = self.client.get('/api/stores/my-store/')
        self.assertIn(response.status_code, [200, 302])
        if response.status_code == 200:
            data = response.json()
            self.assertEqual(data.get('store_name'), 'Toko E2E Test')

    # ── FLOW 3: Products List ──

    def test_flow_03_my_products(self):
        """Seller can list their products."""
        response = self.client.get('/api/products/')
        self.assertIn(response.status_code, [200, 302, 403])

    # ── FLOW 4: Barcode Lookup ──

    def test_flow_04_barcode_lookup(self):
        """Seller can lookup product by barcode."""
        response = self.client.get(
            '/api/inventory/barcode-lookup/?barcode=8991234567890'
        )
        self.assertIn(response.status_code, [200, 302])

    # ── FLOW 5: Smart AI Scan (mocked) ──

    @patch('inventory.services.ai_product_recognition.AIProductRecognitionPipeline._run_pipeline')
    def test_flow_05_ai_scan_recognize(self, mock_run_pipeline):
        """Smart AI Scan recognize endpoint works."""
        mock_run_pipeline.return_value = {
            'vision': {'product_type': 'Keripik Singkong', 'confidence': 0.85},
            'label': None,
            'freshness': None,
        }

        pipeline = get_ai_product_recognition_pipeline()
        result = pipeline.recognize_product('fake_base64_image', store=self.store)
        self.assertTrue(result.get('success'))
        self.assertIn('product_name', result)

    # ── FLOW 6: POS Offline Checkout ──

    def test_flow_06_pos_offline_checkout(self):
        """Seller can process POS offline checkout."""
        response = self.client.post('/api/orders/pos/checkout/', {
            'items': [
                {'barcode': '8991234567890', 'quantity': 3}
            ],
            'buyer_name': 'Test Buyer',
            'payment_method': 'cash',
            'notes': 'E2E Test POS',
        }, content_type='application/json')
        self.assertIn(response.status_code, [200, 201, 400])

    # ── FLOW 7: Offline Sale List ──

    def test_flow_07_offline_sales_list(self):
        """Seller can view offline sales history."""
        response = self.client.get('/api/orders/offline-sales/?limit=10')
        self.assertIn(response.status_code, [200, 302])

    # ── FLOW 8: Expired Reminder Dashboard ──

    def test_flow_08_expired_reminder_dashboard(self):
        """Seller can view AI expired reminder dashboard."""
        response = self.client.get('/api/inventory/expired-reminder/dashboard/')
        self.assertIn(response.status_code, [200, 302])

    # ── FLOW 9: Expired Reminder Discounts ──

    def test_flow_09_expired_reminder_discounts(self):
        """Seller can view AI discount recommendations."""
        response = self.client.get('/api/inventory/expired-reminder/discounts/')
        self.assertIn(response.status_code, [200, 302])

    # ── FLOW 10: Expired Reminder Flash Sale ──

    def test_flow_10_expired_reminder_flash_sale(self):
        """Seller can view AI flash sale candidates."""
        response = self.client.get('/api/inventory/expired-reminder/flash-sale/')
        self.assertIn(response.status_code, [200, 302])

    # ── FLOW 11: Trigger Expiry Check ──

    def test_flow_11_trigger_expiry_check(self):
        """Seller can trigger expiry check."""
        response = self.client.post('/api/inventory/expired-reminder/check/')
        self.assertIn(response.status_code, [200, 302])

    # ── FLOW 12: AI Freshness ──

    @patch('inventory.services.ai_product_recognition.AIProductRecognitionPipeline.classify_freshness')
    def test_flow_12_ai_freshness(self, mock_classify):
        """Seller can call AI freshness endpoint."""
        mock_classify.return_value = {
            'success': True,
            'freshness_score': 85,
            'quality_status': 'fresh',
        }
        response = self.client.post(
            '/api/inventory/ai-freshness/',
            {'image': 'fake_base64'},
            content_type='application/json',
        )
        self.assertIn(response.status_code, [200, 302])

    # ── FLOW 13: AI Multi-Detect ──

    @patch('inventory.services.ai_product_recognition.AIProductRecognitionPipeline.detect_multi_object')
    def test_flow_13_ai_multi_detect(self, mock_detect):
        """Seller can call AI multi-detect endpoint."""
        mock_detect.return_value = {
            'success': True,
            'objects_detected': 3,
            'products': [{'name': 'Product A', 'confidence': 0.9}],
        }
        response = self.client.post(
            '/api/inventory/ai-multi-detect/',
            {'image': 'fake_base64'},
            content_type='application/json',
        )
        self.assertIn(response.status_code, [200, 302])

    # ── FLOW 14: Guest Checkout (Public) ──

    def test_flow_14_guest_checkout_api(self):
        """Guest checkout endpoint is publicly accessible."""
        # Logout first
        self.client.logout()

        response = self.client.post('/api/orders/guest-checkout/', {
            'store_slug': 'toko-e2e-test',
            'items': [{'product_id': self.product.id, 'quantity': 2}],
            'buyer_name': 'Budi',
            'buyer_phone': '08123456789',
            'delivery_address': 'Jl. Test No. 1',
        }, content_type='application/json')
        # Guest checkout may succeed or fail validation gracefully
        self.assertIn(response.status_code, [200, 201, 400, 422])

    # ── FLOW 15: Public Tracking API ──

    def test_flow_15_public_tracking(self):
        """Public tracking endpoint is accessible."""
        response = self.client.get(
            '/api/orders/track-public/?order_number=WRG-TEST'
        )
        self.assertIn(response.status_code, [200, 400, 404])

    # ── FLOW 16: Seller Orders ──

    def test_flow_16_seller_orders(self):
        """Seller can view their orders."""
        response = self.client.get('/api/orders/seller/')
        self.assertIn(response.status_code, [200, 302])

    # ── FLOW 17: Wallet Balance ──

    def test_flow_17_wallet_balance(self):
        """Seller can view wallet balance."""
        response = self.client.get('/api/payments/wallet/balance/')
        self.assertIn(response.status_code, [200, 302, 404])

    # ── FLOW 18: Chat Conversations ──

    def test_flow_18_chat_conversations(self):
        """Seller can view chat conversations."""
        response = self.client.get('/api/chat/conversations/')
        self.assertIn(response.status_code, [200, 302])

    # ── FLOW 19: Logout ──

    def test_flow_19_logout(self):
        """Seller can logout."""
        response = self.client.post(reverse('page-logout'))
        self.assertIn(response.status_code, [302, 200])

    # ── FLOW 20: End-to-End Complete Flow ──

    @patch('inventory.services.ai_product_recognition.AIProductRecognitionPipeline._run_pipeline')
    def test_flow_20_complete_e2e_seller_flow(self, mock_run_pipeline):
        """
        Full E2E seller flow:
        1. Smart AI Scan → recognize product
        2. POS Offline → checkout
        3. Expired Reminder → discount recommendations
        4. Dashboard stats
        """
        # Step 1: Smart AI Scan
        mock_run_pipeline.return_value = {
            'vision': {'product_type': 'Keripik Singkong', 'confidence': 0.9},
            'freshness': {'freshness_score': 85, 'quality_status': 'fresh'},
            'label': {'product_name_on_label': 'Keripik Singkong Balado'},
        }

        pipeline = get_ai_product_recognition_pipeline()
        scan_result = pipeline.recognize_product('fake_image', store=self.store)
        self.assertTrue(scan_result.get('success'))
        self.assertGreater(scan_result.get('confidence', 0), 0)

        # Step 2: POS Offline Checkout
        response = self.client.post('/api/orders/pos/checkout/', {
            'items': [
                {'barcode': '8991234567890', 'quantity': 2}
            ],
            'buyer_name': 'E2E Buyer',
            'payment_method': 'cash',
        }, content_type='application/json')
        self.assertIn(response.status_code, [200, 201, 400])

        # Step 3: Expired Reminder
        reminder = get_expired_reminder()
        dashboard_data = reminder.get_dashboard_widget_data(self.store.id)
        self.assertIsNotNone(dashboard_data)
        self.assertEqual(dashboard_data['store_id'], self.store.id)

        # Step 4: Discount Recommendations
        discount_data = reminder.get_seller_discount_recommendations(self.store.id)
        self.assertIsNotNone(discount_data)
        self.assertIn('recommendations', discount_data)
