"""
Tests for AI Smart Inventory Scanning.
Covers models, services (detection, OCR, barcode, aggregator), and API views.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from stores.models import Store
from inventory.models import (
    MasterProduct, ProductBatch, SmartScanSession, DetectedItem, InventoryStock
)


# =============================================================================
# HELPERS
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


def create_master_product(barcode='8991234567895', name='Beras Premium 5kg'):
    return MasterProduct.objects.create(
        barcode=barcode,
        product_name=name,
        brand='TestBrand',
        category='Sembako',
        unit='karung',
    )


def create_session(store, user, mode='multi'):
    return SmartScanSession.objects.create(
        store=store,
        user=user,
        scan_mode=mode,
        status='scanning',
    )


# =============================================================================
# MODEL TESTS
# =============================================================================


class SmartScanSessionModelTest(TestCase):
    def setUp(self):
        self.user = create_user()
        self.store = create_store(self.user)
        self.session = create_session(self.store, self.user)

    def test_create_session(self):
        self.assertEqual(self.session.status, 'scanning')
        self.assertEqual(self.session.scan_mode, 'multi')
        self.assertEqual(self.session.frame_count, 0)

    def test_session_str(self):
        self.assertIn(str(self.session.id), str(self.session))
        self.assertIn('Toko Test', str(self.session))

    def test_completion_rate_zero(self):
        self.assertEqual(self.session.completion_rate, 0.0)

    def test_duration_seconds(self):
        self.assertGreaterEqual(self.session.duration_seconds, 0)


class DetectedItemModelTest(TestCase):
    def setUp(self):
        self.user = create_user()
        self.store = create_store(self.user)
        self.master = create_master_product()
        self.session = create_session(self.store, self.user)

    def test_create_detected_item(self):
        item = DetectedItem.objects.create(
            session=self.session,
            store=self.store,
            detection_method='barcode',
            confidence_score=0.95,
            master_product=self.master,
            detected_count=10,
            confirmed_count=10,
            detected_barcode=self.master.barcode,
        )
        self.assertEqual(item.detection_method, 'barcode')
        self.assertEqual(item.detected_count, 10)
        self.assertEqual(item.confirmation_status, 'pending')

    def test_item_str_with_master(self):
        item = DetectedItem.objects.create(
            session=self.session,
            store=self.store,
            detection_method='object_detection',
            confidence_score=0.85,
            master_product=self.master,
            detected_count=5,
            confirmed_count=5,
        )
        self.assertIn('Beras Premium', str(item))
        self.assertIn('object_detection', str(item))

    def test_item_auto_confirmed_count(self):
        """Saving with accepted status should auto-set confirmed_count."""
        item = DetectedItem.objects.create(
            session=self.session,
            store=self.store,
            detection_method='barcode',
            confidence_score=0.90,
            detected_count=12,
            confirmed_count=0,
            confirmation_status='accepted',
        )
        self.assertEqual(item.confirmed_count, 12)

    def test_detection_method_choices(self):
        for method, _ in DetectedItem.DETECTION_METHOD_CHOICES:
            item = DetectedItem.objects.create(
                session=self.session,
                store=self.store,
                detection_method=method,
                confidence_score=0.80,
                detected_count=1,
                confirmed_count=1,
            )
            self.assertEqual(item.detection_method, method)


# =============================================================================
# SERVICES — DETECTION
# =============================================================================


class DetectionServiceTest(TestCase):
    def setUp(self):
        self.user = create_user()
        self.store = create_store(self.user)
        self.master = create_master_product()
        self.session = create_session(self.store, self.user)

    def test_process_frame_detections_new_items(self):
        from inventory.ai_scan.services.detection_service import process_frame_detections
        detections = [
            {'label': 'Beras Premium 5kg', 'confidence': 0.92, 'features': {}},
            {'label': 'Minyak Goreng 1L', 'confidence': 0.88, 'features': {}},
        ]
        result = process_frame_detections(self.session, detections, frame_number=1)
        self.assertEqual(result['new_items'], 2)
        self.assertEqual(result['total_detected_in_frame'], 2)

    def test_process_frame_detections_with_count(self):
        from inventory.ai_scan.services.detection_service import process_frame_detections
        detections = [
            {
                'label': 'Beras Premium 5kg',
                'confidence': 0.95,
                'features': {'stack_count': 6},
            },
        ]
        result = process_frame_detections(self.session, detections, frame_number=1)
        self.assertEqual(result['new_items'], 1)
        item = DetectedItem.objects.filter(session=self.session).first()
        self.assertEqual(item.detected_count, 6)

    def test_detect_matches_master_product(self):
        """Label matching should find existing MasterProduct."""
        from inventory.ai_scan.services.detection_service import process_frame_detections
        detections = [
            {'label': 'Beras Premium 5kg', 'confidence': 0.95, 'features': {}},
        ]
        process_frame_detections(self.session, detections, frame_number=1)
        item = DetectedItem.objects.filter(session=self.session).first()
        self.assertEqual(item.master_product, self.master)

    def test_dedup_same_label(self):
        from inventory.ai_scan.services.detection_service import (
            process_frame_detections, deduplicate_session
        )
        # Submit same product twice
        detections = [
            {'label': 'Beras Premium 5kg', 'confidence': 0.9, 'features': {}},
        ]
        process_frame_detections(self.session, detections, frame_number=1)
        process_frame_detections(self.session, detections, frame_number=2)
        
        result = deduplicate_session(self.session)
        self.assertGreaterEqual(result['merged'], 1)

    def test_aggregate_session_detections(self):
        from inventory.ai_scan.services.detection_service import (
            process_frame_detections, aggregate_session_detections
        )
        detections = [
            {'label': 'Beras Premium 5kg', 'confidence': 0.95, 'features': {}},
            {'label': 'Minyak Goreng', 'confidence': 0.85, 'features': {}},
        ]
        process_frame_detections(self.session, detections, frame_number=1)
        aggregated = aggregate_session_detections(self.session)
        self.assertEqual(len(aggregated), 2)


# =============================================================================
# SERVICES — BARCODE
# =============================================================================


class BarcodeServiceTest(TestCase):
    def setUp(self):
        self.user = create_user()
        self.store = create_store(self.user)
        self.master = create_master_product()
        self.session = create_session(self.store, self.user)

    def test_process_barcode_detections_matched(self):
        from inventory.ai_scan.services.barcode_service import process_barcode_detections
        barcodes = [
            {'value': self.master.barcode, 'confidence': 0.98, 'format': 'ean13'},
        ]
        result = process_barcode_detections(self.session, barcodes)
        self.assertEqual(result['matched'], 0)  # First time = new
        self.assertEqual(result['new_items'], 1)
        self.assertEqual(result['errors'], 0)

    def test_process_barcode_detections_unmatched(self):
        from inventory.ai_scan.services.barcode_service import process_barcode_detections
        barcodes = [
            {'value': '0000000000000', 'confidence': 0.95, 'format': 'ean13'},
        ]
        result = process_barcode_detections(self.session, barcodes)
        self.assertEqual(result['new_items'], 1)

    def test_process_bulk_barcodes(self):
        from inventory.ai_scan.services.barcode_service import process_bulk_barcodes
        batch = [
            {'barcode': self.master.barcode, 'count': 12, 'batch_number': 'B001'},
            {'barcode': '0000000000000', 'count': 6},
        ]
        result = process_bulk_barcodes(self.session, batch)
        self.assertEqual(result['total_items'], 18)
        self.assertEqual(result['matched'], 1)
        self.assertEqual(result['new_items'], 1)


# =============================================================================
# SERVICES — OCR
# =============================================================================


class OCRServiceTest(TestCase):
    def setUp(self):
        self.user = create_user()
        self.store = create_store(self.user)
        self.master = create_master_product()
        self.session = create_session(self.store, self.user)

    def test_process_ocr_text_basic(self):
        from inventory.ai_scan.services.ocr_service import process_ocr_text
        text = "Beras Premium 5kg\nEXP: 31/12/2027\nLot: BATCH001\nBPOM: MD 231456789012"
        result = process_ocr_text(text)
        self.assertTrue(result['success'])
        self.assertEqual(result['extracted']['batch_number'], 'BATCH001')
        self.assertIsNotNone(result['extracted']['expiry_date'])

    def test_process_ocr_empty(self):
        from inventory.ai_scan.services.ocr_service import process_ocr_text
        result = process_ocr_text('')
        self.assertFalse(result['success'])

    def test_process_ocr_expiry_date(self):
        from inventory.ai_scan.services.ocr_service import process_ocr_text
        text = "EXP: 12/2027"
        result = process_ocr_text(text)
        self.assertTrue(result['success'])
        self.assertIsNotNone(result['extracted']['expiry_date'])
        self.assertIn('expiry_date', result['uncertain_fields'])

    def test_process_ocr_no_date(self):
        from inventory.ai_scan.services.ocr_service import process_ocr_text
        text = "Product Name\nSome description"
        result = process_ocr_text(text)
        self.assertTrue(result['success'])
        self.assertIsNone(result['extracted']['expiry_date'])


# =============================================================================
# SERVICES — AGGREGATOR
# =============================================================================


class AggregatorServiceTest(TestCase):
    def setUp(self):
        self.user = create_user()
        self.store = create_store(self.user)
        self.master = create_master_product()
        self.session = create_session(self.store, self.user)

        # Create some detected items
        self.item1 = DetectedItem.objects.create(
            session=self.session,
            store=self.store,
            detection_method='barcode',
            confidence_score=0.95,
            master_product=self.master,
            detected_count=10,
            confirmed_count=10,
            detected_barcode=self.master.barcode,
        )
        self.item2 = DetectedItem.objects.create(
            session=self.session,
            store=self.store,
            detection_method='object_detection',
            confidence_score=0.85,
            detected_count=5,
            confirmed_count=5,
            detected_product_name='Unknown Product',
        )

    def test_aggregate_scan_results(self):
        from inventory.ai_scan.services.aggregator_service import aggregate_scan_results
        result = aggregate_scan_results(self.session)
        self.assertEqual(result['session_id'], self.session.id)
        self.assertIn('items', result)
        self.assertIn('summary', result)

    def test_aggregate_summary_counts(self):
        from inventory.ai_scan.services.aggregator_service import aggregate_scan_results
        result = aggregate_scan_results(self.session)
        self.assertEqual(result['summary']['total_items'], 2)
        self.assertEqual(result['summary']['matched_to_master'], 1)
        self.assertEqual(result['summary']['unmatched'], 1)

    def test_register_new_product(self):
        from inventory.ai_scan.services.aggregator_service import register_new_product
        data = {
            'barcode': '8991234567890',
            'product_name': 'Minyak Goreng 1L',
            'brand': 'TestBrand',
            'category': 'Minuman',
            'unit': 'botol',
        }
        result = register_new_product(self.session, data, self.user)
        self.assertTrue(result['success'])
        self.assertEqual(result['master_product']['product_name'], 'Minyak Goreng 1L')

    def test_register_existing_product_returns_existing(self):
        from inventory.ai_scan.services.aggregator_service import register_new_product
        data = {
            'barcode': self.master.barcode,
            'product_name': 'Duplikat',
        }
        result = register_new_product(self.session, data, self.user)
        self.assertTrue(result['success'])
        self.assertEqual(result['master_product']['id'], self.master.id)

    def test_confirm_and_save_items(self):
        from inventory.ai_scan.services.aggregator_service import confirm_and_save_items
        confirmed = [
            {
                'item_id': self.item1.id,
                'confirmed_count': 10,
                'batch_number': 'BATCH-TEST-001',
                'expiry_date': (timezone.now().date() + timedelta(days=365)).isoformat(),
            },
        ]
        result = confirm_and_save_items(self.session, confirmed, self.user)
        self.assertTrue(result['success'])
        self.assertEqual(result['total_batches'], 1)

    def test_get_scan_summary(self):
        from inventory.ai_scan.services.aggregator_service import get_scan_summary
        summary = get_scan_summary(self.store, self.user, days=7)
        self.assertEqual(summary['store_id'], self.store.id)
        self.assertEqual(summary['sessions']['total'], 1)


# =============================================================================
# API TESTS
# =============================================================================


class SmartScanAPITest(APITestCase):
    def setUp(self):
        self.user = create_user()
        self.store = create_store(self.user)
        self.master = create_master_product()
        self.client.force_authenticate(user=self.user)

    def test_start_scan_session(self):
        url = reverse('ai-scan-start')
        resp = self.client.post(url, {'scan_mode': 'multi'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn('session', resp.data)
        self.assertEqual(resp.data['session']['scan_mode'], 'multi')

    def test_start_session_cancels_previous(self):
        url = reverse('ai-scan-start')
        self.client.post(url, {'scan_mode': 'multi'}, format='json')
        resp2 = self.client.post(url, {'scan_mode': 'single'}, format='json')
        self.assertEqual(resp2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp2.data['session']['scan_mode'], 'single')

    def test_session_list(self):
        create_session(self.store, self.user)
        create_session(self.store, self.user)
        url = reverse('ai-scan-sessions')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.data), 2)

    def test_active_session(self):
        create_session(self.store, self.user)
        url = reverse('ai-scan-active')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('session', resp.data)

    def test_submit_frame(self):
        session = create_session(self.store, self.user)
        url = reverse('ai-scan-frame', args=[session.id])
        data = {
            'frame_number': 1,
            'detections': [
                {'label': 'Beras Premium 5kg', 'confidence': 0.92, 'features': {}},
            ],
            'barcodes': [
                {'value': self.master.barcode, 'confidence': 0.98, 'format': 'ean13'},
            ],
            'ocr_text': 'EXP: 12/2027\nBatch: B001',
        }
        resp = self.client.post(url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['success'])
        self.assertIn('results', resp.data)

    def test_submit_frame_invalid_session(self):
        url = reverse('ai-scan-frame', args=[9999])
        resp = self.client.post(url, {'frame_number': 1}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_bulk_barcode_scan(self):
        session = create_session(self.store, self.user)
        url = reverse('ai-scan-bulk', args=[session.id])
        data = {
            'barcodes': [
                {'barcode': self.master.barcode, 'count': 12, 'batch_number': 'B001'},
                {'barcode': '0000000000000', 'count': 6},
            ],
        }
        resp = self.client.post(url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['success'])
        self.assertEqual(resp.data['result']['total_items'], 18)

    def test_review_aggregated(self):
        session = create_session(self.store, self.user)
        DetectedItem.objects.create(
            session=session, store=self.store,
            detection_method='barcode', confidence_score=0.95,
            master_product=self.master, detected_count=10, confirmed_count=10,
        )
        url = reverse('ai-scan-review', args=[session.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['session_id'], session.id)

    def test_update_detected_item(self):
        session = create_session(self.store, self.user)
        item = DetectedItem.objects.create(
            session=session, store=self.store,
            detection_method='barcode', confidence_score=0.90,
            master_product=self.master, detected_count=5, confirmed_count=5,
        )
        url = reverse('ai-scan-item-update', args=[session.id, item.id])
        resp = self.client.patch(url, {'confirmed_count': 8}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['success'])
        self.assertEqual(resp.data['item']['confirmed_count'], 8)

    def test_confirm_and_save(self):
        session = create_session(self.store, self.user)
        item = DetectedItem.objects.create(
            session=session, store=self.store,
            detection_method='barcode', confidence_score=0.95,
            master_product=self.master, detected_count=10, confirmed_count=10,
            detected_barcode=self.master.barcode,
        )
        url = reverse('ai-scan-confirm', args=[session.id])
        data = {
            'items': [
                {
                    'item_id': item.id,
                    'confirmed_count': 10,
                    'batch_number': 'BATCH-TEST',
                    'expiry_date': (timezone.now().date() + timedelta(days=365)).isoformat(),
                },
            ],
        }
        resp = self.client.post(url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['success'])
        self.assertEqual(resp.data['total_batches'], 1)

    def test_register_new_product_from_scan(self):
        session = create_session(self.store, self.user)
        url = reverse('ai-scan-register', args=[session.id])
        data = {
            'barcode': '8991234567890',
            'product_name': 'Minyak Goreng 1L',
            'brand': 'TestBrand',
            'category': 'Minuman',
            'unit': 'botol',
        }
        resp = self.client.post(url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp.data['success'])

    def test_reject_all_pending(self):
        session = create_session(self.store, self.user)
        DetectedItem.objects.create(
            session=session, store=self.store,
            detection_method='barcode', confidence_score=0.90,
            detected_count=3, confirmed_count=3,
        )
        url = reverse('ai-scan-reject', args=[session.id])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['items_rejected'], 1)

    def test_scan_summary(self):
        session = create_session(self.store, self.user)
        # Complete a session
        session.status = 'saved'
        session.total_items_detected = 10
        session.total_items_confirmed = 8
        session.total_batches_created = 3
        session.save()

        url = reverse('ai-scan-summary')
        resp = self.client.get(url, {'days': 7})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['store_id'], self.store.id)

    def test_cancel_session(self):
        session = create_session(self.store, self.user)
        url = reverse('ai-scan-cancel', args=[session.id])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        session.refresh_from_db()
        self.assertEqual(session.status, 'cancelled')

    def test_unauthenticated_access(self):
        self.client.force_authenticate(user=None)
        url = reverse('ai-scan-start')
        resp = self.client.post(url, {'scan_mode': 'multi'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_detected_item_list(self):
        session = create_session(self.store, self.user)
        DetectedItem.objects.create(
            session=session, store=self.store,
            detection_method='barcode', confidence_score=0.95,
            master_product=self.master, detected_count=5, confirmed_count=5,
        )
        url = reverse('ai-scan-items', args=[session.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.data), 1)

    def test_session_detail(self):
        session = create_session(self.store, self.user)
        url = reverse('ai-scan-detail', args=[session.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['session_id'], session.id)

    def test_full_scan_workflow(self):
        """End-to-end test: start → frame → review → confirm."""
        # Start
        url_start = reverse('ai-scan-start')
        resp = self.client.post(url_start, {'scan_mode': 'multi'}, format='json')
        session_id = resp.data['session']['id']

        # Submit frame
        url_frame = reverse('ai-scan-frame', args=[session_id])
        frame_data = {
            'detections': [
                {'label': 'Beras Premium 5kg', 'confidence': 0.95, 'features': {'stack_count': 5}},
            ],
            'barcodes': [
                {'value': self.master.barcode, 'confidence': 0.99, 'format': 'ean13'},
            ],
        }
        resp = self.client.post(url_frame, frame_data, format='json')
        self.assertTrue(resp.data['success'])

        # Review
        url_review = reverse('ai-scan-review', args=[session_id])
        resp = self.client.get(url_review)
        self.assertGreater(len(resp.data['items']), 0)

        # Confirm
        url_confirm = reverse('ai-scan-confirm', args=[session_id])
        items = resp.data['items']
        confirm_data = {
            'items': [
                {
                    'item_id': items[0]['item_ids'][0],
                    'confirmed_count': items[0]['confirmed_count'],
                    'batch_number': 'BATCH-E2E',
                    'expiry_date': (timezone.now().date() + timedelta(days=365)).isoformat(),
                },
            ],
        }
        resp = self.client.post(url_confirm, confirm_data, format='json')
        self.assertTrue(resp.data['success'])
        self.assertGreaterEqual(resp.data['total_batches'], 1)
