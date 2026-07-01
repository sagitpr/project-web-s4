"""
Comprehensive tests for inventory management.
Covers models, services (barcode, FEFO, expiry), and all API views.
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from accounts.models import User
from stores.models import Store
from products.models import Category as ProductCategory, Product

from .models import (
    MasterProduct, ProductBatch, InventoryStock,
    ExpiryNotification, StockAlert,
)
from .services.barcode_lookup import (
    lookup_barcode, detect_barcode_format, validate_barcode_checksum,
)
from .services.fefo_engine import (
    stock_in, stock_out, get_fefo_batch, get_batch_summary, get_expiry_summary,
)
from .services.expiry_service import check_and_notify_expiry


# =============================================================================
# HELPER FACTORIES
# =============================================================================


def create_user(phone='08123456789', role='seller'):
    email = f'{role}_{phone}@test.com'
    return User.objects.create_user(
        username=email.split('@')[0],
        email=email,
        phone=phone,
        password='testpass123',
        full_name=f'Test {role.title()}',
        role=role,
    )


def create_store(user, name='Toko Test'):
    return Store.objects.create(
        user=user,
        store_name=name,
        address='Jl. Test No. 1',
        city='Jakarta',
        province='DKI Jakarta',
    )


def create_master_product(barcode='8991234567890', name='Produk Test'):
    return MasterProduct.objects.create(
        barcode=barcode,
        product_name=name,
        brand='TestBrand',
        category='Makanan',
        unit='pcs',
    )


def create_batch(store, master, batch_no='B001', qty=100,
                 prod_date=None, expiry_date=None):
    if prod_date is None:
        prod_date = timezone.now().date() - timedelta(days=30)
    if expiry_date is None:
        expiry_date = timezone.now().date() + timedelta(days=300)
    return ProductBatch.objects.create(
        store=store,
        master_product=master,
        batch_number=batch_no,
        production_date=prod_date,
        expiry_date=expiry_date,
        initial_quantity=qty,
        current_quantity=qty,
        unit='pcs',
    )


# =============================================================================
# MODEL TESTS
# =============================================================================


class MasterProductModelTest(TestCase):
    def setUp(self):
        self.product = create_master_product()

    def test_create_master_product(self):
        self.assertEqual(self.product.barcode, '8991234567890')
        self.assertEqual(self.product.product_name, 'Produk Test')
        self.assertTrue(self.product.is_active)

    def test_master_product_str(self):
        self.assertIn('Produk Test', str(self.product))
        self.assertIn('8991234567890', str(self.product))

    def test_unique_barcode(self):
        with self.assertRaises(Exception):
            create_master_product(barcode='8991234567890', name='Duplikat')


class ProductBatchModelTest(TestCase):
    def setUp(self):
        self.user = create_user()
        self.store = create_store(self.user)
        self.master = create_master_product()
        self.batch = create_batch(self.store, self.master)

    def test_create_batch(self):
        self.assertEqual(self.batch.batch_number, 'B001')
        self.assertEqual(self.batch.current_quantity, Decimal('100'))

    def test_auto_shelf_life_calculation(self):
        prod = timezone.now().date() - timedelta(days=30)
        expiry = timezone.now().date() + timedelta(days=270)
        total_shelf = (expiry - prod).days  # 300 days
        batch = create_batch(self.store, self.master, 'B002',
                             prod_date=prod, expiry_date=expiry)
        self.assertEqual(batch.shelf_life_days, total_shelf)
        # 30 days elapsed out of 300 → 90% remaining
        expected_pct = round(((total_shelf - 30) / total_shelf) * 100, 2)
        self.assertEqual(batch.shelf_life_remaining_pct, Decimal(str(expected_pct)))

    def test_auto_status_fresh(self):
        self.assertEqual(self.batch.status, 'fresh')

    def test_auto_status_expiring_soon(self):
        expiry = timezone.now().date() + timedelta(days=10)
        batch = create_batch(self.store, self.master, 'B003',
                             expiry_date=expiry)
        self.assertEqual(batch.status, 'expiring_soon')

    def test_auto_status_expired(self):
        expiry = timezone.now().date() - timedelta(days=1)
        batch = create_batch(self.store, self.master, 'B004',
                             expiry_date=expiry)
        self.assertEqual(batch.status, 'expired')

    def test_auto_status_disposed(self):
        batch = create_batch(self.store, self.master, 'B005', qty=0)
        self.assertEqual(batch.status, 'disposed')

    def test_days_until_expiry(self):
        # batch created with 300 days to expiry
        expiry = timezone.now().date() + timedelta(days=300)
        batch = create_batch(self.store, self.master, 'B006',
                             expiry_date=expiry)
        self.assertEqual(batch.days_until_expiry, 300)


class InventoryStockModelTest(TestCase):
    def setUp(self):
        self.user = create_user()
        self.store = create_store(self.user)
        self.master = create_master_product()
        self.batch = create_batch(self.store, self.master, qty=100)

    def test_create_transaction(self):
        txn = InventoryStock.objects.create(
            store=self.store,
            master_product=self.master,
            batch=self.batch,
            transaction_type='stock_in',
            quantity=Decimal('100'),
            quantity_before=Decimal('0'),
            quantity_after=Decimal('100'),
        )
        self.assertEqual(txn.transaction_type, 'stock_in')
        self.assertEqual(txn.quantity, Decimal('100'))


class StockAlertModelTest(TestCase):
    def setUp(self):
        self.user = create_user()
        self.store = create_store(self.user)
        self.master = create_master_product()

    def test_create_alert(self):
        alert = StockAlert.objects.create(
            store=self.store,
            master_product=self.master,
            min_stock=10,
            max_stock=500,
        )
        self.assertEqual(alert.min_stock, Decimal('10'))
        self.assertTrue(alert.is_active)

    def test_unique_together(self):
        StockAlert.objects.create(
            store=self.store,
            master_product=self.master,
            min_stock=10,
        )
        with self.assertRaises(Exception):
            StockAlert.objects.create(
                store=self.store,
                master_product=self.master,
                min_stock=20,
            )


# =============================================================================
# BARCODE SERVICE TESTS
# =============================================================================


class BarcodeServiceTest(TestCase):
    def test_detect_ean13(self):
        self.assertEqual(detect_barcode_format('8991234567890'), 'ean13')

    def test_detect_ean8(self):
        self.assertEqual(detect_barcode_format('12345678'), 'ean8')

    def test_detect_upca(self):
        self.assertEqual(detect_barcode_format('123456789012'), 'upca')

    def test_detect_invalid(self):
        self.assertIsNone(detect_barcode_format('abc'))
        self.assertIsNone(detect_barcode_format(''))

    def test_validate_checksum_valid_ean13(self):
        # Valid EAN-13 checksum: 8991234567890 → check digit = 0
        # Sum of odd positions (0-indexed) = 9+9+2+4+6+8 = 38
        # Sum of even positions = 8+1+3+5+7+9 = 33
        # Total = 38*3 + 33 = 147
        # (10 - (147 % 10)) % 10 = (10 - 7) % 10 = 3
        # Wait, that doesn't match. Let me compute differently.
        # digits = [8,9,9,1,2,3,4,5,6,7,8,9,0]
        # check = 0 (last digit)
        # For EAN-13 length=13: even positions (0,2,4,6,8,10) get weight 3, odd (1,3,5,7,9,11) get weight 1
        # Hmm the function logic is:
        #   weight = 3 if (i % 2 == 0 if length == 13 else i % 2 == 1) else 1
        # For EAN-13 (length=13): weight = 3 if i % 2 == 0 else 1
        # So digits at index 0,2,4,6,8,10 get weight 3
        # digits at index 1,3,5,7,9,11 get weight 1
        # 8*3 + 9*1 + 9*3 + 1*1 + 2*3 + 3*1 + 4*3 + 5*1 + 6*3 + 7*1 + 8*3 + 9*1
        # = 24 + 9 + 27 + 1 + 6 + 3 + 12 + 5 + 18 + 7 + 24 + 9 = 145
        # (10 - (145 % 10)) % 10 = (10 - 5) % 10 = 5
        # So check digit should be 5, not 0
        # Let me use a known valid EAN-13
        self.assertTrue(validate_barcode_checksum('8991234567895'))

    def test_validate_checksum_invalid(self):
        self.assertFalse(validate_barcode_checksum('8991234567890'))
        self.assertFalse(validate_barcode_checksum('abc'))

    def test_validate_checksum_empty(self):
        self.assertFalse(validate_barcode_checksum(''))

    def test_lookup_local_found(self):
        master = create_master_product()
        result = lookup_barcode(master.barcode)
        self.assertTrue(result['found'])
        self.assertEqual(result['source'], 'local')

    def test_lookup_local_not_found(self):
        result = lookup_barcode('0000000000000')
        self.assertFalse(result['found'])
        # Since external API may not have this, source will be 'error' or 'external'
        self.assertIn(result['source'], ['error', 'external'])

    def test_lookup_invalid_barcode(self):
        result = lookup_barcode('abc')
        self.assertFalse(result['found'])
        self.assertEqual(result['source'], 'error')


# =============================================================================
# FEFO ENGINE TESTS
# =============================================================================


class FEFOEngineTest(TestCase):
    def setUp(self):
        self.user = create_user()
        self.store = create_store(self.user)
        self.master = create_master_product()
        today = timezone.now().date()

        # Create batches with different expiry dates
        self.batch_far = create_batch(
            self.store, self.master, 'FAR', qty=50,
            expiry_date=today + timedelta(days=200),
        )
        self.batch_near = create_batch(
            self.store, self.master, 'NEAR', qty=30,
            expiry_date=today + timedelta(days=30),
        )
        self.batch_mid = create_batch(
            self.store, self.master, 'MID', qty=40,
            expiry_date=today + timedelta(days=100),
        )

    def test_stock_in_new_batch(self):
        result = stock_in(
            store=self.store,
            master_product=self.master,
            batch_number='NEWBATCH',
            production_date=timezone.now().date() - timedelta(days=10),
            expiry_date=timezone.now().date() + timedelta(days=355),
            quantity=Decimal('200'),
        )
        self.assertTrue(result['success'])
        self.assertTrue(result['is_new_batch'])
        self.assertEqual(result['batch'].current_quantity, Decimal('200'))

    def test_stock_in_existing_batch(self):
        # Add more stock to existing batch
        result = stock_in(
            store=self.store,
            master_product=self.master,
            batch_number='NEAR',
            production_date=self.batch_near.production_date,
            expiry_date=self.batch_near.expiry_date,
            quantity=Decimal('20'),
        )
        self.assertTrue(result['success'])
        self.assertFalse(result['is_new_batch'])
        self.assertEqual(result['batch'].current_quantity, Decimal('50'))

    def test_fefo_picks_nearest_expiry_first(self):
        """FEFO should pick batch with nearest expiry date first."""
        result = get_fefo_batch(self.store, self.master, Decimal('40'))
        self.assertTrue(result['success'])
        # Should pick from NEAR (30) + MID (10)
        picks = result['picks']
        self.assertEqual(len(picks), 2)
        self.assertEqual(picks[0]['batch'].batch_number, 'NEAR')
        self.assertEqual(picks[1]['batch'].batch_number, 'MID')

    def test_fefo_picks_single_batch(self):
        """When one batch has enough stock, only pick from it."""
        result = get_fefo_batch(self.store, self.master, Decimal('20'))
        self.assertTrue(result['success'])
        self.assertEqual(len(result['picks']), 1)
        self.assertEqual(result['picks'][0]['batch'].batch_number, 'NEAR')

    def test_fefo_insufficient_stock(self):
        """Should return error when total stock < requested quantity."""
        result = get_fefo_batch(self.store, self.master, Decimal('999'))
        self.assertFalse(result['success'])
        self.assertIn('Stok tidak mencukupi', result['error'])

    def test_stock_out_fefo(self):
        """Stock out should deduct from nearest-expiring batch first."""
        result = stock_out(
            store=self.store,
            master_product=self.master,
            quantity=Decimal('60'),
            notes='Test FEFO',
        )
        self.assertTrue(result['success'])
        self.assertEqual(result['batches_used'], 2)
        self.assertEqual(result['total_quantity'], 60.0)

        # Refresh from DB
        self.batch_near.refresh_from_db()
        self.batch_mid.refresh_from_db()
        self.batch_far.refresh_from_db()

        # NEAR should be depleted (30 - 30 = 0)
        self.assertEqual(self.batch_near.current_quantity, Decimal('0'))
        # MID should have 10 left (40 - 30 = 10, since need 60 total, 30 from NEAR + 30 from MID)
        self.assertEqual(self.batch_mid.current_quantity, Decimal('10'))
        # FAR should be untouched
        self.assertEqual(self.batch_far.current_quantity, Decimal('50'))

    def test_batch_summary(self):
        summary = get_batch_summary(self.store)
        self.assertEqual(summary['total_batches'], 3)
        self.assertEqual(summary['total_stock_qty'], 120)

    def test_batch_summary_filter_by_product(self):
        summary = get_batch_summary(self.store, self.master)
        self.assertEqual(summary['total_batches'], 3)

    def test_expiry_summary(self):
        summary = get_expiry_summary(self.store)
        # NEAR expires in 30 days, so it should appear in monthly but not necessarily weekly
        self.assertIn('expiring_this_week_count', summary)
        self.assertIn('already_expired_count', summary)


# =============================================================================
# EXPIRY SERVICE TESTS
# =============================================================================


class ExpiryServiceTest(TestCase):
    def setUp(self):
        self.user = create_user()
        self.store = create_store(self.user)
        self.master = create_master_product()

        # Create an expiring batch (within 30 days)
        self.expiring_batch = create_batch(
            self.store, self.master, 'EXP30', qty=20,
            expiry_date=timezone.now().date() + timedelta(days=15),
        )
        # Create an already expired batch
        self.expired_batch = create_batch(
            self.store, self.master, 'EXP0', qty=5,
            expiry_date=timezone.now().date() - timedelta(days=3),
        )

    def test_check_and_notify_expiry_sends_notifications(self):
        result = check_and_notify_expiry(self.store)
        self.assertGreaterEqual(result['expiring_soon'], 1)
        self.assertGreaterEqual(result['expired'], 1)
        self.assertIn('expiring_soon', result)
        self.assertIn('expired', result)

    def test_check_and_notify_expiry_is_idempotent(self):
        """Running twice should not send duplicate notifications."""
        result1 = check_and_notify_expiry(self.store)
        result2 = check_and_notify_expiry(self.store)
        # Second run should send 0 new notifications
        self.assertEqual(result2['expiring_soon'], 0)
        self.assertEqual(result2['expired'], 0)

    def test_expiry_notification_created(self):
        check_and_notify_expiry(self.store)
        self.assertTrue(
            ExpiryNotification.objects.filter(
                batch=self.expiring_batch,
                notification_type='expiring_soon',
            ).exists()
        )
        self.assertTrue(
            ExpiryNotification.objects.filter(
                batch=self.expired_batch,
                notification_type='expired',
            ).exists()
        )


# =============================================================================
# API TESTS
# =============================================================================


class InventoryAPITest(APITestCase):
    def setUp(self):
        self.user = create_user()
        self.store = create_store(self.user)
        self.master = create_master_product()
        create_batch(self.store, self.master, 'API_BATCH', qty=100)

        # Authenticate
        self.client.force_authenticate(user=self.user)

    def test_barcode_lookup_found(self):
        url = reverse('barcode-lookup')
        resp = self.client.get(url, {'barcode': self.master.barcode})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['found'])
        self.assertEqual(resp.data['source'], 'local')

    def test_barcode_lookup_not_found(self):
        url = reverse('barcode-lookup')
        resp = self.client.get(url, {'barcode': '0000000000000'})
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(resp.data['found'])

    def test_barcode_lookup_no_barcode(self):
        url = reverse('barcode-lookup')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_master_product_search(self):
        url = reverse('master-product-search')
        resp = self.client.get(url, {'q': 'Produk'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.data), 1)

    def test_master_product_detail(self):
        url = reverse('master-product-detail', args=[self.master.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['barcode'], self.master.barcode)

    def test_create_master_product(self):
        url = reverse('master-product-create')
        data = {
            'barcode': '8991234567895',
            'product_name': 'Produk Baru',
            'brand': 'Merek Baru',
            'category': 'Minuman',
            'unit': 'pcs',
        }
        resp = self.client.post(url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp.data['found'])

    def test_create_master_product_duplicate_barcode(self):
        """Should return 200 with existing product for duplicate barcode."""
        url = reverse('master-product-create')
        data = {
            'barcode': self.master.barcode,
            'product_name': 'Duplikat',
        }
        resp = self.client.post(url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['found'])

    def test_create_batch(self):
        url = reverse('batch-create')
        today = timezone.now().date()
        data = {
            'master_product_id': self.master.id,
            'batch_number': 'BATCH-API-001',
            'production_date': (today - timedelta(days=30)).isoformat(),
            'expiry_date': (today + timedelta(days=270)).isoformat(),
            'quantity': '500',
            'unit': 'pcs',
        }
        resp = self.client.post(url, data, format='json')
        if resp.status_code != status.HTTP_201_CREATED:
            print('ERROR:', resp.data)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp.data['success'])

    def test_batch_list(self):
        url = reverse('batch-list')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.data), 1)

    def test_batch_detail(self):
        batch = ProductBatch.objects.first()
        url = reverse('batch-detail', args=[batch.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['batch_number'], batch.batch_number)

    def test_batch_summary(self):
        url = reverse('batch-summary')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('total_batches', resp.data)

    def test_stock_out(self):
        """Test FEFO stock outbound via API."""
        url = reverse('stock-out')
        data = {
            'master_product_id': self.master.id,
            'quantity': '30',
            'notes': 'Test penjualan',
        }
        resp = self.client.post(url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['success'])
        self.assertEqual(resp.data['total_quantity'], 30.0)

    def test_stock_out_insufficient(self):
        """Test stock out with insufficient quantity returns 409."""
        url = reverse('stock-out')
        data = {
            'master_product_id': self.master.id,
            'quantity': '99999',
        }
        resp = self.client.post(url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)
        self.assertFalse(resp.data['success'])

    def test_fefo_check(self):
        """Test FEFO preview endpoint."""
        url = reverse('fefo-check')
        data = {
            'master_product_id': self.master.id,
            'quantity': '30',
        }
        resp = self.client.post(url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['success'])

    def test_inventory_transactions(self):
        """Test transaction list endpoint."""
        url = reverse('transaction-list')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # May be 0 since we haven't created transactions via API
        self.assertIsInstance(resp.data, list)

    def test_stock_out_creates_transaction(self):
        """Stock out should create InventoryStock records."""
        url = reverse('stock-out')
        data = {
            'master_product_id': self.master.id,
            'quantity': '10',
        }
        self.client.post(url, data, format='json')
        txn_count = InventoryStock.objects.filter(
            store=self.store,
            transaction_type='stock_out',
        ).count()
        self.assertEqual(txn_count, 1)

    def test_expiry_summary(self):
        url = reverse('expiry-summary')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('expiring_this_week_count', resp.data)

    def test_expiry_check_trigger(self):
        url = reverse('expiry-check')
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['success'])

    def test_expiry_notifications_list(self):
        url = reverse('expiry-notifications')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_alert_list_create(self):
        url = reverse('alert-list-create')
        data = {
            'master_product': self.master.id,
            'min_stock': 10,
            'max_stock': 500,
        }
        resp = self.client.post(url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_low_stock_report(self):
        """Test low stock report endpoint."""
        StockAlert.objects.create(
            store=self.store,
            master_product=self.master,
            min_stock=200,  # Higher than current 100 stock
        )
        url = reverse('low-stock-report')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('total_low_stock', resp.data)

    def test_batch_dispose(self):
        """Test batch disposal via API."""
        batch = ProductBatch.objects.first()
        url = reverse('batch-dispose', args=[batch.id])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['success'])
        # Verify batch is marked as inactive
        batch.refresh_from_db()
        self.assertEqual(batch.current_quantity, Decimal('0'))
        self.assertFalse(batch.is_active)

    def test_unauthenticated_access(self):
        """Test that unauthenticated requests are rejected."""
        self.client.force_authenticate(user=None)
        url = reverse('batch-summary')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
