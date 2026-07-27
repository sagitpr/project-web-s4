"""
Unit tests for AI Expired Reminder service.
Tests discount tiers, bundling suggestions, flash sale candidates,
dashboard widget data, and notification deduplication.
"""

from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.utils import timezone

from inventory.services.expired_reminder import (
    AIExpiredReminder,
    get_expired_reminder,
    DISCOUNT_TIERS,
)


class AIExpiredReminderTest(TestCase):
    """Test suite for AIExpiredReminder."""

    def setUp(self):
        self.reminder = AIExpiredReminder()

    def test_initialization(self):
        """Reminder should initialize without error."""
        reminder = get_expired_reminder()
        self.assertIsNotNone(reminder)
        self.assertTrue(hasattr(reminder, 'check_store_expiry'))
        self.assertTrue(hasattr(reminder, 'recommend_discount'))
        self.assertTrue(hasattr(reminder, 'suggest_bundling'))
        self.assertTrue(hasattr(reminder, 'get_flash_sale_candidates'))
        self.assertTrue(hasattr(reminder, 'get_seller_discount_recommendations'))
        self.assertTrue(hasattr(reminder, 'get_dashboard_widget_data'))

    def test_discount_tiers_structure(self):
        """DISCOUNT_TIERS should have 4 tiers with correct structure."""
        self.assertEqual(len(DISCOUNT_TIERS), 4)
        for tier in DISCOUNT_TIERS:
            self.assertIn('days_min', tier)
            self.assertIn('days_max', tier)
            self.assertIn('discount_pct', tier)
            self.assertIn('type', tier)
            self.assertIn('label', tier)
            self.assertIn('urgency', tier)

    def test_discount_tiers_are_contiguous(self):
        """Discount tiers should cover 0-30 days without gaps."""
        sorted_tiers = sorted(DISCOUNT_TIERS, key=lambda t: t['days_min'])
        for i in range(len(sorted_tiers) - 1):
            self.assertEqual(sorted_tiers[i]['days_max'] + 1, sorted_tiers[i + 1]['days_min'])
        self.assertEqual(sorted_tiers[0]['days_min'], 0)
        self.assertEqual(sorted_tiers[-1]['days_max'], 30)

    def test_discount_tiers_discount_decreasing(self):
        """Earlier expiry should have higher discount percentage."""
        sorted_tiers = sorted(DISCOUNT_TIERS, key=lambda t: t['days_min'])
        for i in range(len(sorted_tiers) - 1):
            self.assertGreaterEqual(
                sorted_tiers[i]['discount_pct'],
                sorted_tiers[i + 1]['discount_pct'],
                f"Tier {i} ({sorted_tiers[i]['days_min']}-{sorted_tiers[i]['days_max']}d) should have >= discount than tier {i + 1}"
            )

    def test_recommend_discount_flash_sale(self):
        """Products <= 3 days should get flash sale (60% discount)."""
        mock_batch = MagicMock()
        mock_batch.id = 1
        mock_batch.master_product.product_name = 'Susu Ultra'
        mock_batch.master_product.barcode = '8991234567890'
        mock_batch.current_quantity = 50
        mock_batch.unit = 'pcs'
        mock_batch.purchase_price = Decimal('5000')

        for days in range(0, 4):
            result = self.reminder.recommend_discount(days, mock_batch)
            self.assertIsNotNone(result, f"No discount for {days} days remaining")
            self.assertEqual(result['discount_type'], 'flash_sale')
            self.assertEqual(result['recommended_discount_pct'], 60)
            self.assertEqual(result['urgency'], 'critical')

    def test_recommend_discount_high(self):
        """Products 4-7 days should get 40% discount with high urgency."""
        mock_batch = MagicMock()
        mock_batch.id = 2
        mock_batch.master_product.product_name = 'Roti Tawar'
        mock_batch.current_quantity = 20
        mock_batch.unit = 'pcs'
        mock_batch.purchase_price = Decimal('10000')

        for days in range(4, 8):
            result = self.reminder.recommend_discount(days, mock_batch)
            self.assertIsNotNone(result)
            self.assertEqual(result['discount_type'], 'discount')
            self.assertEqual(result['urgency'], 'high')

    def test_recommend_discount_medium(self):
        """Products 8-14 days should get 25% discount with medium urgency."""
        mock_batch = MagicMock()
        mock_batch.id = 3
        mock_batch.master_product.product_name = 'Mie Instant'
        mock_batch.current_quantity = 100
        mock_batch.unit = 'pcs'
        mock_batch.purchase_price = Decimal('2500')

        for days in range(8, 15):
            result = self.reminder.recommend_discount(days, mock_batch)
            self.assertIsNotNone(result)
            self.assertEqual(result['discount_type'], 'discount')

    def test_recommend_discount_low(self):
        """Products 15-30 days should get 15% promo with low urgency."""
        mock_batch = MagicMock()
        mock_batch.id = 4
        mock_batch.master_product.product_name = 'Kopi Bubuk'
        mock_batch.current_quantity = 30
        mock_batch.unit = 'pcs'
        mock_batch.purchase_price = Decimal('15000')

        for days in range(15, 31):
            result = self.reminder.recommend_discount(days, mock_batch)
            self.assertIsNotNone(result)
            self.assertEqual(result['discount_type'], 'promo')
            self.assertEqual(result['urgency'], 'low')

    def test_recommend_discount_no_tier(self):
        """Days > 30 should return None (no discount needed)."""
        mock_batch = MagicMock()
        mock_batch.id = 5
        mock_batch.master_product.product_name = 'Produk Baru'
        mock_batch.current_quantity = 10
        mock_batch.unit = 'pcs'
        result = self.reminder.recommend_discount(60, mock_batch)
        self.assertIsNone(result)

    def test_recommend_discount_suggested_price(self):
        """Discount recommendation should include suggested_price."""
        mock_batch = MagicMock()
        mock_batch.id = 6
        mock_batch.master_product.product_name = 'Minyak Goreng'
        mock_batch.current_quantity = 24
        mock_batch.unit = 'botol'
        mock_batch.purchase_price = Decimal('20000')

        result = self.reminder.recommend_discount(3, mock_batch)
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.get('suggested_price'))
        # 20000 * 1.3 = 26000 original, 60% off = 10400
        self.assertAlmostEqual(result['suggested_price'], 10400, delta=100)

    def test_suggest_bundling_empty(self):
        """Empty expiring batches should return empty list."""
        result = self.reminder.suggest_bundling([])
        self.assertEqual(result, [])

    def test_suggest_bundling_single(self):
        """Single batch should return empty list."""
        batches = [
            {'product_name': 'Susu', 'category': 'Minuman', 'days_remaining': 3, 'current_quantity': 10}
        ]
        result = self.reminder.suggest_bundling(batches)
        self.assertEqual(result, [])

    def test_suggest_bundling_same_category(self):
        """Two batches in same category should create bundle."""
        batches = [
            {'product_name': 'Susu Ultra', 'category': 'Minuman', 'days_remaining': 3, 'current_quantity': 10},
            {'product_name': 'Jus Jeruk', 'category': 'Minuman', 'days_remaining': 5, 'current_quantity': 8},
        ]
        result = self.reminder.suggest_bundling(batches)
        self.assertGreater(len(result), 0)
        self.assertIn('bundle_name', result[0])
        self.assertEqual(len(result[0]['products']), 2)

    def test_suggest_bundling_max_suggestions(self):
        """Should respect max_suggestions parameter."""
        batches = [
            {'product_name': f'Produk {i}', 'category': 'Makanan', 'days_remaining': i, 'current_quantity': 5}
            for i in range(1, 10)
        ]
        result = self.reminder.suggest_bundling(batches, max_suggestions=3)
        self.assertLessEqual(len(result), 3)

    def test_get_flash_sale_candidates_empty(self):
        """Should return empty list when DB has no data (no store)."""
        result = self.reminder.get_flash_sale_candidates(store_id=99999)
        self.assertEqual(result, [])

    def test_dashboard_widget_data(self):
        """Dashboard widget data should have expected structure."""
        result = self.reminder.get_dashboard_widget_data(store_id=99999)
        self.assertIn('store_id', result)
        self.assertIn('total_stock', result)
        self.assertIn('fresh_stock', result)
        self.assertIn('expiring_soon_stock', result)
        self.assertIn('expired_stock', result)
        self.assertIn('nearest_expiring', result)

    def test_get_seller_discount_recommendations(self):
        """Seller discount recommendations should have expected structure."""
        result = self.reminder.get_seller_discount_recommendations(store_id=99999)
        self.assertIn('store_id', result)
        self.assertIn('total_expiring', result)
        self.assertIn('recommendations', result)
        self.assertIn('financial_impact', result)
        self.assertIn('generated_at', result)

    def test_financial_impact_calculation(self):
        """Financial impact should calculate recovery rate."""
        result = self.reminder.get_seller_discount_recommendations(store_id=99999)
        fi = result.get('financial_impact', {})
        self.assertIn('total_stock_value_at_risk', fi)
        self.assertIn('potential_recovery_with_discount', fi)
        self.assertIn('recovery_rate_pct', fi)

    def test_discount_message_flash_sale(self):
        """Flash sale discount should contain urgency markers."""
        mock_batch = MagicMock()
        mock_batch.id = 1
        mock_batch.master_product.product_name = 'Yogurt'
        mock_batch.current_quantity = Decimal('15')
        mock_batch.unit = 'cup'

        result = self.reminder.recommend_discount(2, mock_batch)
        self.assertIsNotNone(result)
        self.assertIn('FLASH SALE', result['suggestion'].upper())
        self.assertIn('60%', result['suggestion'])

    def test_singleton(self):
        """get_expired_reminder should return singleton."""
        r1 = get_expired_reminder()
        r2 = get_expired_reminder()
        self.assertIs(r1, r2)

    def test_global_expiry_check_empty(self):
        """run_global_expiry_check should work with no stores."""
        result = self.reminder.run_global_expiry_check()
        self.assertIn('stores_checked', result)
        self.assertIn('total_batches_checked', result)
        self.assertIn('total_notifications_sent', result)
