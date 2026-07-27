"""
Unit tests for QR code generation and verification service.

Tests:
- generate_qr_code() returns valid format strings
- generate_qr_code() is unique per call
- verify_qr_code() accepts valid codes
- verify_qr_code() rejects invalid/mismatched codes
- verify_qr_code() rejects already-completed deliveries
- Verify both pickup and delivery code types
"""

import pytest
from unittest.mock import MagicMock
from orders.services.qr import generate_qr_code, verify_qr_code


@pytest.fixture
def mock_delivery():
    """Create a mock Delivery object with proper attributes."""
    d = MagicMock()
    d.id = 42
    d.order_id = 100
    d.qr_pickup_code = None
    d.qr_delivery_code = None
    d.picked_up_at = None
    d.delivered_at = None
    return d


class TestGenerateQRCode:
    """Test QR code generation."""

    def test_generate_returns_string(self, mock_delivery):
        """QR code should be a non-empty string."""
        code = generate_qr_code(mock_delivery, 'pickup')
        assert isinstance(code, str)
        assert len(code) > 20

    def test_generate_format(self, mock_delivery):
        """QR code should start with WRG-PICKUP or WRG-DELIVERY."""
        pickup = generate_qr_code(mock_delivery, 'pickup')
        delivery = generate_qr_code(mock_delivery, 'delivery')
        assert pickup.startswith('WRG-PICKUP-')
        assert delivery.startswith('WRG-DELIVERY-')

    def test_generate_unique_per_call(self, mock_delivery):
        """Each call should produce a unique code (UUID is embedded)."""
        code1 = generate_qr_code(mock_delivery, 'pickup')
        code2 = generate_qr_code(mock_delivery, 'pickup')
        assert code1 != code2

    def test_generate_has_signature(self, mock_delivery):
        """QR code should have an HMAC signature as the last segment."""
        code = generate_qr_code(mock_delivery, 'pickup')
        parts = code.split('-')
        assert len(parts) >= 6  # WRG-PICKUP-DELIVERY_ID-ORDER_ID-UUID-SIGNATURE
        # Last segment should be 8-char uppercase hex
        signature = parts[-1]
        assert len(signature) == 8
        assert signature.isalnum()

    def test_generate_delivery_code(self, mock_delivery):
        """Delivery code type should produce correct prefix."""
        code = generate_qr_code(mock_delivery, 'delivery')
        assert code.startswith('WRG-DELIVERY-')

    def test_generate_pickup_code(self, mock_delivery):
        """Pickup code type should produce correct prefix."""
        code = generate_qr_code(mock_delivery, 'pickup')
        assert code.startswith('WRG-PICKUP-')


class TestVerifyQRCode:
    """Test QR code verification."""

    def test_verify_valid_code(self, mock_delivery):
        """A freshly generated code should verify successfully."""
        code = generate_qr_code(mock_delivery, 'pickup')
        mock_delivery.qr_pickup_code = code
        result = verify_qr_code(mock_delivery, code, 'pickup')
        assert result['valid'] is True

    def test_verify_valid_delivery_code(self, mock_delivery):
        """Delivery code should verify successfully."""
        code = generate_qr_code(mock_delivery, 'delivery')
        mock_delivery.qr_delivery_code = code
        result = verify_qr_code(mock_delivery, code, 'delivery')
        assert result['valid'] is True

    def test_verify_wrong_code_rejected(self, mock_delivery):
        """Wrong QR code should be rejected."""
        code = generate_qr_code(mock_delivery, 'pickup')
        mock_delivery.qr_pickup_code = code
        result = verify_qr_code(mock_delivery, 'WRG-PICKUP-FAKE-12345-ABCD', 'pickup')
        assert result['valid'] is False
        assert 'tidak cocok' in result.get('error', '').lower()

    def test_verify_mismatched_type_rejected(self, mock_delivery):
        """A pickup code used for delivery verification should be rejected."""
        code = generate_qr_code(mock_delivery, 'pickup')
        mock_delivery.qr_pickup_code = code
        # Try to verify pickup code as delivery code
        result = verify_qr_code(mock_delivery, code, 'delivery')
        assert result['valid'] is False

    def test_verify_already_picked_up_rejected(self, mock_delivery):
        """Already picked up delivery should reject pickup code."""
        code = generate_qr_code(mock_delivery, 'pickup')
        mock_delivery.qr_pickup_code = code
        mock_delivery.picked_up_at = MagicMock()  # already picked up
        result = verify_qr_code(mock_delivery, code, 'pickup')
        assert result['valid'] is False
        assert 'sudah' in result.get('error', '').lower()

    def test_verify_already_delivered_rejected(self, mock_delivery):
        """Already delivered delivery should reject delivery code."""
        code = generate_qr_code(mock_delivery, 'delivery')
        mock_delivery.qr_delivery_code = code
        mock_delivery.delivered_at = MagicMock()  # already delivered
        result = verify_qr_code(mock_delivery, code, 'delivery')
        assert result['valid'] is False

    def test_verify_no_code_generated(self, mock_delivery):
        """If no QR code has been generated, verification should fail."""
        result = verify_qr_code(mock_delivery, 'SOME-CODE', 'pickup')
        assert result['valid'] is False
        assert 'belum dibuat' in result.get('error', '').lower()

    def test_verify_tampered_code_rejected(self, mock_delivery):
        """Tampered HMAC signature should be detected."""
        code = generate_qr_code(mock_delivery, 'pickup')
        mock_delivery.qr_pickup_code = code
        # Tamper the signature — store a different code so QR mismatch is caught at HMAC level
        # But first the stored-code check must pass. So also update stored code.
        parts = code.split('-')
        parts[-1] = 'DEADBEEF'  # wrong signature
        tampered = '-'.join(parts)
        # Update stored code to match tampered code so we reach HMAC check
        mock_delivery.qr_pickup_code = tampered
        result = verify_qr_code(mock_delivery, tampered, 'pickup')
        assert result['valid'] is False
        assert 'tanda tangan' in result.get('error', '').lower()

    def test_verify_case_insensitive(self, mock_delivery):
        """Verification should be case-insensitive."""
        code = generate_qr_code(mock_delivery, 'pickup')
        mock_delivery.qr_pickup_code = code
        # Lower case should match (code is uppercase, but verify uses .upper() internally)
        result = verify_qr_code(mock_delivery, code.lower(), 'pickup')
        assert result['valid'] is True
