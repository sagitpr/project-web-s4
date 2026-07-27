"""
Unit tests for AI Product Recognition Pipeline service.
Tests the parallelized pipeline, _safe_call, _merge_pipeline_results,
freshness classification, multi-object detection, and UMKM learning.
"""

from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch, MagicMock, Mock
from django.test import TestCase, override_settings

from inventory.services.ai_product_recognition import (
    AIProductRecognitionPipeline,
    get_ai_product_recognition_pipeline,
    AUTO_CONFIDENCE_THRESHOLD,
    SCAN_TIMEOUT_SECONDS,
)


class AIProductRecognitionPipelineTest(TestCase):
    """Test suite for AIProductRecognitionPipeline."""

    def setUp(self):
        self.pipeline = AIProductRecognitionPipeline()
        # Mock Gemini and Vision clients to avoid real API calls
        self.pipeline.gemini = MagicMock()
        self.pipeline.vision = MagicMock()

    def test_initialization(self):
        """Pipeline should initialize without error."""
        pipeline = get_ai_product_recognition_pipeline()
        self.assertIsNotNone(pipeline)
        self.assertTrue(hasattr(pipeline, 'recognize_product'))
        self.assertTrue(hasattr(pipeline, 'detect_multi_object'))
        self.assertTrue(hasattr(pipeline, 'classify_freshness'))
        self.assertTrue(hasattr(pipeline, 'learn_new_product'))

    def test_safe_call_success(self):
        """_safe_call should return the function result on success."""
        mock_func = MagicMock(return_value={'result': 'ok'})
        result = self.pipeline._safe_call(mock_func, 'arg1', kwarg='val1')
        self.assertEqual(result, {'result': 'ok'})
        mock_func.assert_called_once_with('arg1', kwarg='val1')

    def test_safe_call_exception(self):
        """_safe_call should return None on exception, not crash."""
        def failing_func(x):
            raise ValueError('test error')
        result = self.pipeline._safe_call(failing_func, 'fail')
        self.assertIsNone(result)

    def test_safe_call_connection_close(self):
        """_safe_call should handle connection close gracefully."""
        mock_func = MagicMock(return_value={'ok': True})
        result = self.pipeline._safe_call(mock_func)
        self.assertEqual(result, {'ok': True})

    def test_merge_pipeline_no_results(self):
        """_merge_pipeline_results should handle empty input."""
        result = self.pipeline._merge_pipeline_results({})
        self.assertIn('product_name', result)
        self.assertEqual(result['product_name'], '')
        self.assertEqual(result['confidence'], 0.0)
        self.assertEqual(result['detection_method'], 'ai_vision')

    def test_merge_pipeline_with_vision(self):
        """_merge_pipeline_results should pick highest confidence name from vision."""
        results = {
            'vision': {
                'product_type': 'Indomie Goreng',
                'confidence': 0.75,
            }
        }
        merged = self.pipeline._merge_pipeline_results(results)
        self.assertEqual(merged['product_name'], 'Indomie Goreng')
        self.assertEqual(merged['confidence'], 0.75)
        self.assertEqual(merged['detection_method'], 'vision')

    def test_merge_pipeline_barcode_wins(self):
        """Barcode lookup should override vision with higher confidence."""
        results = {
            'vision': {
                'product_type': 'Mie Instant',
                'confidence': 0.6,
            },
            'barcode': {
                'found': True,
                'master_product': {
                    'product_name': 'Indomie Goreng Rasa Ayam',
                    'barcode': '8991234567890',
                    'brand': 'Indomie',
                    'category': 'Makanan',
                    'unit': 'pcs',
                    'id': 123,
                }
            }
        }
        merged = self.pipeline._merge_pipeline_results(results)
        self.assertEqual(merged['product_name'], 'Indomie Goreng Rasa Ayam')
        self.assertEqual(merged['barcode'], '8991234567890')
        self.assertEqual(merged['confidence'], 0.95)
        self.assertEqual(merged['detection_method'], 'barcode_db')

    def test_merge_pipeline_freshness_overrides(self):
        """Freshness analysis should override confidence when higher."""
        results = {
            'freshness': {
                'product_type': 'Pisang Cavendish',
                'confidence': 0.88,
                'freshness_score': 92,
                'quality_status': 'fresh',
                'recommendation': 'Simpan di suhu ruang',
            }
        }
        merged = self.pipeline._merge_pipeline_results(results)
        self.assertEqual(merged['product_name'], 'Pisang Cavendish')
        self.assertGreaterEqual(merged['confidence'], 0.88)
        self.assertEqual(merged['freshness_score'], 92)
        self.assertEqual(merged['detection_method'], 'freshness')

    def test_merge_pipeline_with_label_ocr(self):
        """Label OCR should extract expiry date and batch number."""
        results = {
            'label': {
                'product_name_on_label': 'Susu Ultra Milk',
                'brand': 'Ultra Milk',
                'expiration_date': '2026-12-31',
                'production_date': '20260101',
                'bpom_number': 'MD 123456789012',
                'confidence': 0.7,
            }
        }
        merged = self.pipeline._merge_pipeline_results(results)
        self.assertEqual(merged['product_name'], 'Susu Ultra Milk')
        self.assertEqual(merged['expiry_date'], '2026-12-31')
        self.assertEqual(merged['bpom_number'], 'MD 123456789012')

    def test_merge_pipeline_with_client_ocr(self):
        """Client OCR hint should be accepted with lower confidence."""
        results = {
            'ocr_hint': {'text': 'Aqua 600ml', 'source': 'client_ocr'}
        }
        merged = self.pipeline._merge_pipeline_results(results)
        self.assertEqual(merged['product_name'], 'Aqua 600ml')
        self.assertEqual(merged['confidence'], 0.4)
        self.assertEqual(merged['detection_method'], 'client_ocr')

    def test_merge_pipeline_multiple_sources(self):
        """Multiple sources should pick the best."""
        results = {
            'vision': {
                'product_type': 'Minuman Teh',
                'confidence': 0.5,
            },
            'label': {
                'product_name_on_label': 'Teh Botol Sosro',
                'brand': 'Sosro',
                'expiration_date': '2027-06-15',
                'confidence': 0.65,
            },
            'barcode': {
                'found': True,
                'master_product': {
                    'product_name': 'Teh Botol Sosro Original 500ml',
                    'barcode': '8991234567890',
                    'brand': 'Sosro',
                    'category': 'Minuman',
                    'unit': 'botol',
                    'id': 456,
                }
            }
        }
        merged = self.pipeline._merge_pipeline_results(results)
        # Barcode should win with highest confidence
        self.assertEqual(merged['product_name'], 'Teh Botol Sosro Original 500ml')
        self.assertEqual(merged['confidence'], 0.95)
        self.assertEqual(merged['barcode'], '8991234567890')

    def test_recognize_product_no_image(self):
        """recognize_product should handle missing image gracefully."""
        result = self.pipeline.recognize_product('', store=None)
        self.assertIn('success', result)
        self.assertTrue(result.get('fallback_needed'))

    def test_auto_register_product_no_barcode_no_name(self):
        """auto_register_product should fail without barcode and name."""
        result = self.pipeline.auto_register_product({}, store=None)
        self.assertFalse(result.get('success'))
        self.assertIn('error', result)

    def test_confidence_threshold_constant(self):
        """AUTO_CONFIDENCE_THRESHOLD should be 0.85."""
        self.assertEqual(AUTO_CONFIDENCE_THRESHOLD, 0.85)

    def test_scan_timeout_constant(self):
        """SCAN_TIMEOUT_SECONDS should be 3."""
        self.assertEqual(SCAN_TIMEOUT_SECONDS, 3)

    def test_classify_freshness_empty_vision(self):
        """classify_freshness should return default response when vision fails."""
        self.pipeline.gemini = MagicMock()
        self.pipeline.vision.analyze_freshness = MagicMock(return_value=None)
        result = self.pipeline.classify_freshness('fake_image', 'Apel')
        self.assertIn('freshness_score', result)
        self.assertIsNone(result['freshness_score'])
        self.assertEqual(result['quality_status'], 'pending')

    def test_detect_multi_object_empty_result(self):
        """detect_multi_object should handle no products detected."""
        self.pipeline.gemini.analyze_image = MagicMock(return_value=None)
        result = self.pipeline.detect_multi_object('fake_image')
        self.assertEqual(result['products'], [])
        self.assertEqual(result['total_unique_products'], 0)

    def test_singleton_pattern(self):
        """get_ai_product_recognition_pipeline should return singleton."""
        p1 = get_ai_product_recognition_pipeline()
        p2 = get_ai_product_recognition_pipeline()
        self.assertIs(p1, p2)

    def test_parallel_pipeline_structure(self):
        """_run_pipeline should return dict with expected keys."""
        # Mock all vision services
        self.pipeline.vision.analyze_product_image = MagicMock(
            return_value={'product_type': 'Test', 'confidence': 0.8}
        )
        self.pipeline.vision.analyze_freshness = MagicMock(
            return_value={'freshness_score': 90, 'quality_status': 'fresh'}
        )
        self.pipeline.vision.scan_label = MagicMock(
            return_value={'product_name_on_label': 'Test Label'}
        )

        results = self.pipeline._run_pipeline(
            'fake_image', barcode_hint='8991234567890', store=None
        )
        self.assertIn('vision', results)
        self.assertIn('freshness', results)
        self.assertIn('label', results)
        # barcode should NOT be in results because lookup_barcode needs DB
        # but the key should exist

    def test_packaging_rejected(self):
        """Vision packaging damage should set freshness_status to rejected."""
        results = {
            'vision': {
                'product_type': 'Susu Kotak',
                'packaging_quality': {
                    'damage_detected': True,
                    'damage_type': 'Bocor',
                    'seal_intact': False,
                }
            }
        }
        merged = self.pipeline._merge_pipeline_results(results)
        self.assertEqual(merged['freshness_status'], 'rejected')
        self.assertIn('tidak dijual', merged['freshness_recommendation'].lower())
