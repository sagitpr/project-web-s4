"""
Tests for the hyperlocal courier tracking service module.

Covers:
- Delivery status label lookup
- Hyperlocal tracking data generation with milestones (step, icon, time, is_current)
- Cache key generation (SHA-256 prefix)
- Cache clearing (specific delivery / all)
- Main get_tracking_status entry point with caching logic
- Edge cases: None delivery, unknown status, terminal status skip-cache
"""

import hashlib
import logging
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest
from django.core.cache import cache
from django.utils import timezone

from orders.services.courier_tracking import (
    get_delivery_status_label,
    get_hyperlocal_tracking,
    get_tracking_status,
    _make_cache_key,
    clear_tracking_cache,
    TRACKING_CACHE_PREFIX,
    TRACKING_CACHE_TTL,
    DELIVERY_STATUS_LABELS,
    HYPELOCAL_COURIERS,
    TRACKING_HISTORY_TEMPLATES,
)


# =============================================================================
# get_delivery_status_label()
# =============================================================================


class TestGetDeliveryStatusLabel:
    """Tests for human-readable status label lookup."""

    def test_known_statuses(self):
        """All registered statuses should return the correct label."""
        cases = {
            'menunggu_konfirmasi': 'Menunggu Konfirmasi',
            'diproses_penjual': 'Diproses Penjual',
            'menunggu_penjemputan': 'Menunggu Penjemputan',
            'kurir_menjemput': 'Kurir Menjemput',
            'dalam_perjalanan': 'Dalam Perjalanan',
            'pesanan_diterima': 'Pesanan Diterima',
            'dibatalkan': 'Dibatalkan',
        }
        for code, expected in cases.items():
            assert get_delivery_status_label(code) == expected

    def test_unknown_status_returns_raw(self):
        """Unknown status codes should be returned as-is."""
        assert get_delivery_status_label('unknown_status') == 'unknown_status'
        assert get_delivery_status_label('') == ''
        assert get_delivery_status_label(None) is None  # noqa

    def test_case_sensitive(self):
        """Lookup should be case-sensitive (uses lowercase DB codes)."""
        label = get_delivery_status_label('MENUNGGU_KONFIRMASI')
        assert label == 'MENUNGGU_KONFIRMASI'  # no match, returned as-is


# =============================================================================
# _make_cache_key()
# =============================================================================


class TestMakeCacheKey:
    """Tests for cache key generation (SHA-256 hash)."""

    def test_key_format_and_prefix(self):
        """Key should start with the tracking prefix and be deterministic."""
        key = _make_cache_key(42, 'menunggu_konfirmasi')
        assert key.startswith(TRACKING_CACHE_PREFIX + ':')
        assert len(key) == len(TRACKING_CACHE_PREFIX) + 1 + 32  # prefix: + sha256[:32]

    def test_deterministic(self):
        """Same inputs should always produce the same key."""
        key1 = _make_cache_key(1, 'dalam_perjalanan')
        key2 = _make_cache_key(1, 'dalam_perjalanan')
        assert key1 == key2

    def test_differs_by_delivery_id(self):
        """Different delivery IDs should produce different keys."""
        key1 = _make_cache_key(1, 'menunggu_konfirmasi')
        key2 = _make_cache_key(2, 'menunggu_konfirmasi')
        assert key1 != key2

    def test_differs_by_status(self):
        """Different statuses should produce different keys."""
        key1 = _make_cache_key(1, 'menunggu_konfirmasi')
        key2 = _make_cache_key(1, 'diproses_penjual')
        assert key1 != key2

    def test_default_status(self):
        """Default status should be 'menunggu_konfirmasi'."""
        key_explicit = _make_cache_key(1, 'menunggu_konfirmasi')
        key_default = _make_cache_key(1)
        assert key_explicit == key_default

    def test_hash_algorithm(self):
        """Internal hash should use SHA-256 truncated to 32 chars."""
        raw = f'{TRACKING_CACHE_PREFIX}:delivery:{99}:pesanan_diterima'
        expected_hash = hashlib.sha256(raw.encode()).hexdigest()[:32]
        expected_key = f'{TRACKING_CACHE_PREFIX}:{expected_hash}'
        assert _make_cache_key(99, 'pesanan_diterima') == expected_key


# =============================================================================
# get_hyperlocal_tracking()  (requires DB for Delivery model)
# =============================================================================


@pytest.mark.django_db
class TestGetHyperlocalTracking:
    """Tests for hyperlocal tracking data generation."""

    @pytest.fixture(autouse=True)
    def _setup(self, request):
        """Create a minimal Delivery instance via conftest-style objects."""
        from django.contrib.auth import get_user_model
        from stores.models import Store, StoreCategory
        from orders.models import Order, Delivery, ShippingMethod

        User = get_user_model()
        self.user = User.objects.create_user(
            username='buyer_track',
            email='buyer_track@test.io',
            password='Pass123!',
            full_name='Buyer Track',
            is_verified=True,
        )
        self.category = StoreCategory.objects.create(name='Test Toko')
        self.store = Store.objects.create(
            user=self.user,
            store_name='Toko Tracking Test',
            slug='toko-tracking-test',
            description='Testing tracking',
            address='Jl. Test No. 1',
            city='Jakarta',
            category=self.category,
            status='active',
        )
        self.order = Order.objects.create(
            user=self.user,
            store=self.store,
            delivery_address='Jl. Buyer No. 10',
            recipient_name='Buyer Track',
            recipient_phone='08123456789',
        )
        self.shipping_method = ShippingMethod.objects.create(
            code='gosend',
            name='GoSend',
            estimated_time='30-45 menit',
            is_active=True,
        )
        self.delivery = Delivery.objects.create(
            order=self.order,
            shipping_method=self.shipping_method,
            courier_name='GoSend',
            driver_name='Budi Driver',
            driver_phone='0811112222',
            pickup_code='ABC123',
            estimated_time='30-45 menit',
            estimated_pickup='10-15 menit',
            delivery_status='menunggu_konfirmasi',
        )

    def test_none_delivery_returns_none(self):
        """Passing None should return None."""
        assert get_hyperlocal_tracking(None) is None

    def test_returns_expected_structure(self):
        """Should return dict with all expected top-level keys."""
        result = get_hyperlocal_tracking(self.delivery)
        expected_keys = {
            'courier', 'delivery_status', 'delivery_status_label',
            'status', 'milestones', 'driver_name', 'driver_phone',
            'pickup_code', 'estimated_time', 'estimated_pickup',
            'estimated_delivery', 'source',
        }
        assert set(result.keys()) == expected_keys
        assert result['source'] == 'hyperlocal'

    def test_menunggu_konfirmasi_milestones(self):
        """Status 'menunggu_konfirmasi' → 1 milestone, step 1."""
        self.delivery.delivery_status = 'menunggu_konfirmasi'
        self.delivery.save()
        result = get_hyperlocal_tracking(self.delivery)
        assert len(result['milestones']) == 1
        assert result['milestones'][0]['step'] == 1
        assert result['milestones'][0]['icon'] == 'package'
        assert result['milestones'][0]['is_current']

    def test_diproses_penjual_milestones(self):
        """Status 'diproses_penjual' → 2 milestones, step 1 & 2."""
        self.delivery.delivery_status = 'diproses_penjual'
        self.delivery.save()
        result = get_hyperlocal_tracking(self.delivery)
        assert len(result['milestones']) == 2
        assert result['milestones'][0]['step'] == 1
        assert result['milestones'][1]['step'] == 2
        assert not result['milestones'][0]['is_current']
        assert result['milestones'][1]['is_current']

    def test_dalam_perjalanan_milestones(self):
        """Status 'dalam_perjalanan' → 5 milestones, current on last."""
        self.delivery.delivery_status = 'dalam_perjalanan'
        self.delivery.save()
        result = get_hyperlocal_tracking(self.delivery)
        assert len(result['milestones']) == 5
        assert result['milestones'][-1]['is_current']
        assert result['milestones'][-1]['icon'] == 'truck'

    def test_pesanan_diterima_no_current(self):
        """Terminal status 'pesanan_diterima': no is_current on any milestone."""
        self.delivery.delivery_status = 'pesanan_diterima'
        self.delivery.save()
        result = get_hyperlocal_tracking(self.delivery)
        assert len(result['milestones']) == 6
        for m in result['milestones']:
            assert not m['is_current']
        assert result['milestones'][-1]['icon'] == 'check'
        assert result['status'] == 'delivered'

    def test_dibatalkan_no_current(self):
        """Terminal status 'dibatalkan': no is_current, icon 'x' on last."""
        self.delivery.delivery_status = 'dibatalkan'
        self.delivery.save()
        result = get_hyperlocal_tracking(self.delivery)
        assert len(result['milestones']) == 2
        for m in result['milestones']:
            assert not m['is_current']
        assert result['milestones'][-1]['icon'] == 'x'
        assert result['status'] == 'cancelled'

    def test_overall_status_mapping(self):
        """Overall 'status' field should map correctly for frontend compatibility."""
        cases = {
            'menunggu_konfirmasi': 'waiting',
            'diproses_penjual': 'waiting',
            'menunggu_penjemputan': 'picked_up',
            'kurir_menjemput': 'picked_up',
            'dalam_perjalanan': 'on_delivery',
            'pesanan_diterima': 'delivered',
            'dibatalkan': 'cancelled',
        }
        for db_status, expected_overall in cases.items():
            self.delivery.delivery_status = db_status
            self.delivery.save()
            result = get_hyperlocal_tracking(self.delivery)
            assert result['status'] == expected_overall, f"Failed for '{db_status}'"

    def test_unknown_status_fallback(self):
        """Unknown delivery_status should fallback to 1-milestone with label."""
        self.delivery.delivery_status = 'unknown_custom_status'
        self.delivery.save()
        result = get_hyperlocal_tracking(self.delivery)
        assert len(result['milestones']) == 1
        assert result['milestones'][0]['icon'] == 'clock'
        assert result['status'] == 'waiting'

    def test_courier_name_resolved(self):
        """Courier name should come from shipping_method.name."""
        result = get_hyperlocal_tracking(self.delivery)
        assert result['courier'] == 'GoSend'

    def test_courier_name_fallback(self):
        """If no shipping_method, fallback to courier_name."""
        self.delivery.shipping_method = None
        self.delivery.courier_name = 'GrabExpress'
        self.delivery.save()
        result = get_hyperlocal_tracking(self.delivery)
        assert result['courier'] == 'GrabExpress'

    def test_driver_info_passthrough(self):
        """Driver name and phone should pass through from the delivery."""
        result = get_hyperlocal_tracking(self.delivery)
        assert result['driver_name'] == 'Budi Driver'
        assert result['driver_phone'] == '0811112222'
        assert result['pickup_code'] == 'ABC123'

    def test_milestones_have_timestamps(self):
        """Each milestone should have a valid ISO-format time string."""
        self.delivery.delivery_status = 'dalam_perjalanan'
        self.delivery.save()
        result = get_hyperlocal_tracking(self.delivery)
        for m in result['milestones']:
            assert 'time' in m
            # Should be parseable as ISO datetime
            datetime.fromisoformat(m['time'])

    def test_milestones_descending_order(self):
        """Milestones should be in chronological order (oldest first)."""
        self.delivery.delivery_status = 'dalam_perjalanan'
        self.delivery.save()
        result = get_hyperlocal_tracking(self.delivery)
        times = [datetime.fromisoformat(m['time']) for m in result['milestones']]
        for i in range(1, len(times)):
            assert times[i - 1] <= times[i]

    def test_milestone_step_sequence(self):
        """Steps should follow the template sequence (1,2,3...)."""
        self.delivery.delivery_status = 'kurir_menjemput'
        self.delivery.save()
        result = get_hyperlocal_tracking(self.delivery)
        steps = [m['step'] for m in result['milestones']]
        assert steps == [1, 2, 3, 4]  # from TRACKING_HISTORY_TEMPLATES


# =============================================================================
# clear_tracking_cache()
# =============================================================================


class TestClearTrackingCache:
    """Tests for cache clearing (uses Django's locmem cache)."""

    def setup_method(self):
        cache.clear()

    @patch('orders.services.courier_tracking.cache')
    def test_clear_specific_delivery(self, mock_cache):
        """Clearing a specific delivery should call cache.delete for each status."""
        clear_tracking_cache(delivery_id=99)
        expected_calls = len(DELIVERY_STATUS_LABELS)
        assert mock_cache.delete.call_count == expected_calls
        # Verify at least one expected key
        expected_key = _make_cache_key(99, 'menunggu_konfirmasi')
        mock_cache.delete.assert_any_call(expected_key)

    @patch('orders.services.courier_tracking.cache')
    def test_clear_all(self, mock_cache):
        """Clearing with no args should call cache.clear()."""
        clear_tracking_cache()
        mock_cache.clear.assert_called_once()

    @patch('orders.services.courier_tracking.logger')
    @patch('orders.services.courier_tracking.cache')
    def test_clear_all_handles_exception(self, mock_cache, mock_logger):
        """Clearing all when cache.clear() fails should log a warning."""
        mock_cache.clear.side_effect = Exception('Cache backend unavailable')
        clear_tracking_cache()
        mock_logger.warning.assert_called_once()
        assert 'Could not clear cache' in mock_logger.warning.call_args[0][0]


# =============================================================================
# get_tracking_status()  — main entry point with caching
# =============================================================================


@pytest.mark.django_db
class TestGetTrackingStatus:
    """Tests for the main synchronous entry point with caching."""

    @pytest.fixture(autouse=True)
    def _setup(self, request):
        from django.contrib.auth import get_user_model
        from stores.models import Store, StoreCategory
        from orders.models import Order, Delivery

        User = get_user_model()
        self.user = User.objects.create_user(
            username='buyer_ts',
            email='buyer_ts@test.io',
            password='Pass123!',
            is_verified=True,
        )
        self.category = StoreCategory.objects.create(name='Test Cat')
        self.store = Store.objects.create(
            user=self.user, store_name='TS Store', slug='ts-store',
            description='Test', address='Addr', city='Jkt',
            category=self.category, status='active',
        )
        self.order = Order.objects.create(
            user=self.user, store=self.store,
            delivery_address='Addr',
            recipient_name='Buyer',
        )
        self.delivery = Delivery.objects.create(
            order=self.order,
            delivery_status='menunggu_konfirmasi',
            driver_name='Driver',
            driver_phone='08123',
        )

    def teardown_method(self):
        cache.clear()

    def test_none_delivery_returns_none(self):
        """Passing None should return None."""
        assert get_tracking_status(None) is None

    def test_returns_tracking_data(self):
        """Should return tracking data for a valid delivery."""
        result = get_tracking_status(self.delivery)
        assert result is not None
        assert result['source'] == 'hyperlocal'
        assert 'milestones' in result
        assert result['delivery_status'] == 'menunggu_konfirmasi'

    def test_cache_hit_on_second_call(self):
        """Second call with same delivery should return cached result."""
        result1 = get_tracking_status(self.delivery)
        assert result1.get('_cache_hit') is None  # first call is NOT a cache hit

        result2 = get_tracking_status(self.delivery)
        assert result2.get('_cache_hit') is True  # second call IS a cache hit

    def test_cache_eviction_after_clear(self):
        """Clearing cache should cause a cache miss."""
        get_tracking_status(self.delivery)  # warm cache
        clear_tracking_cache(delivery_id=self.delivery.id)
        result = get_tracking_status(self.delivery)
        assert result.get('_cache_hit') is None  # miss after clear

    def test_terminal_status_skips_cache(self):
        """Terminal statuses (delivered/cancelled) should not be cached."""
        self.delivery.delivery_status = 'pesanan_diterima'
        self.delivery.save()

        result1 = get_tracking_status(self.delivery)
        assert result1.get('_cache_hit') is None

        result2 = get_tracking_status(self.delivery)
        # Even the second call should miss cache for terminal statuses
        assert result2.get('_cache_hit') is None

    def test_cancelled_also_skips_cache(self):
        """'dibatalkan' should also skip cache."""
        self.delivery.delivery_status = 'dibatalkan'
        self.delivery.save()
        get_tracking_status(self.delivery)  # warm
        result = get_tracking_status(self.delivery)  # should miss
        assert result.get('_cache_hit') is None

    def test_different_statuses_independent_cache(self):
        """Different delivery statuses should have independent cache entries."""
        get_tracking_status(self.delivery)  # menunggu_konfirmasi

        self.delivery.delivery_status = 'diproses_penjual'
        self.delivery.save()
        result = get_tracking_status(self.delivery)  # different status → miss
        assert result.get('_cache_hit') is None

        # Original status should still be cached
        # But we need to re-set the status — cache is keyed by delivery_id + status
        self.delivery.delivery_status = 'menunggu_konfirmasi'
        self.delivery.save()
        cached = get_tracking_status(self.delivery)
        assert cached.get('_cache_hit') is True


# =============================================================================
# Module-level constants sanity
# =============================================================================


class TestModuleConstants:
    """Sanity checks for module-level constants."""

    def test_tracking_cache_ttl(self):
        """Cache TTL should be exactly 5 minutes (300 seconds)."""
        expected = 60 * 5
        assert TRACKING_CACHE_TTL == expected

    def test_hyperlocal_couriers_defined(self):
        """Should define all 4 hyperlocal couriers."""
        assert len(HYPELOCAL_COURIERS) == 4
        assert 'gosend' in HYPELOCAL_COURIERS
        assert 'grabexpress' in HYPELOCAL_COURIERS
        assert 'maxim' in HYPELOCAL_COURIERS
        assert 'antar_sendiri' in HYPELOCAL_COURIERS

    def test_delivery_status_labels_count(self):
        """Should have labels for all 7 delivery statuses."""
        assert len(DELIVERY_STATUS_LABELS) == 7

    def test_tracking_history_templates_count(self):
        """Should have templates for all 7 statuses."""
        assert len(TRACKING_HISTORY_TEMPLATES) == 7

    def test_all_statuses_have_label(self):
        """Every status in TRACKING_HISTORY_TEMPLATES should have a label."""
        for status in TRACKING_HISTORY_TEMPLATES:
            assert status in DELIVERY_STATUS_LABELS


# =============================================================================
# Integration: get_tracking_status → get_hyperlocal_tracking data consistency
# =============================================================================


@pytest.mark.django_db
class TestTrackingDataConsistency:
    """Ensures the output of get_tracking_status is internally consistent."""

    @pytest.fixture(autouse=True)
    def _setup(self, request):
        from django.contrib.auth import get_user_model
        from stores.models import Store, StoreCategory
        from orders.models import Order, Delivery

        User = get_user_model()
        self.user = User.objects.create_user(
            username='consistency',
            email='consistency@test.io',
            password='Pass123!',
            is_verified=True,
        )
        category = StoreCategory.objects.create(name='Cat')
        store = Store.objects.create(
            user=self.user, store_name='Con Store', slug='con-store',
            description='', address='A', city='Jkt',
            category=category, status='active',
        )
        order = Order.objects.create(
            user=self.user, store=store,
            delivery_address='Addr', recipient_name='R',
        )
        self.delivery = Delivery.objects.create(
            order=order, delivery_status='dalam_perjalanan',
            driver_name='Agus', driver_phone='081',
            pickup_code='XYZ',
        )

    def teardown_method(self):
        cache.clear()

    def test_status_matches(self):
        """Top-level status should be consistent with milestones."""
        result = get_tracking_status(self.delivery)
        assert result['status'] == 'on_delivery'
        assert result['delivery_status'] == 'dalam_perjalanan'

    def test_milestones_have_all_required_fields(self):
        """Every milestone should have step, status, icon, time, is_current."""
        result = get_tracking_status(self.delivery)
        for m in result['milestones']:
            assert 'step' in m
            assert 'status' in m
            assert 'icon' in m
            assert 'time' in m
            assert 'is_current' in m

    def test_non_terminal_milestone_current_flag(self):
        """Non-terminal status should have exactly one current milestone (the last)."""
        result = get_tracking_status(self.delivery)
        current_count = sum(1 for m in result['milestones'] if m['is_current'])
        assert current_count == 1
        # The last milestone should be the current one
        assert result['milestones'][-1]['is_current']

    def test_driver_info_preserved_in_full_flow(self):
        """Driver/pickup info should survive the full get_tracking_status flow."""
        result = get_tracking_status(self.delivery)
        assert result['driver_name'] == 'Agus'
        assert result['driver_phone'] == '081'
        assert result['pickup_code'] == 'XYZ'
