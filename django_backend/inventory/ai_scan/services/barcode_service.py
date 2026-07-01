"""
Enhanced Barcode Service for AI Smart Inventory Scanning.

Handles:
- Multi-barcode detection per camera frame
- EAN-13, EAN-8, UPC-A barcode support
- Barcode stacking detection (multiple barcodes on shelf)
- Auto-matching to MasterProduct database
- Duplicate suppression across frames
- Batch barcode scanning (bulk shelf scan)
"""

import logging

from ...models import MasterProduct, DetectedItem
from inventory.services.barcode_lookup import lookup_barcode, detect_barcode_format

logger = logging.getLogger('django_backend.inventory.ai_scan.barcode')


def process_barcode_detections(session, barcodes, frame_number=0):
    """
    Process multiple barcode detections from a single camera frame.
    
    Returns dict with matched, new, and error counts.
    """
    store = session.store
    matched = 0
    new_items = 0
    errors = 0
    new_master_products = 0

    for bc in barcodes:
        value = bc.get('value', '').strip()
        confidence = min(float(bc.get('confidence', 0.8)), 1.0)
        bbox = bc.get('bbox')
        fmt = bc.get('format', detect_barcode_format(value))

        if not value or not fmt:
            errors += 1
            continue

        lookup_result = lookup_barcode(value, store=store)

        if lookup_result.get('found'):
            master = lookup_result.get('master_product')
            if lookup_result.get('is_new'):
                new_master_products += 1

            existing = DetectedItem.objects.filter(
                session=session,
                detected_barcode=value,
                confirmation_status='pending',
            ).first()

            if existing:
                existing.detected_count += 1
                existing.confidence_score = max(existing.confidence_score, confidence)
                existing.save(update_fields=[
                    'detected_count', 'confidence_score', 'updated_at',
                ])
                matched += 1
            else:
                DetectedItem.objects.create(
                    session=session, store=store,
                    detection_method='barcode',
                    confidence_score=confidence,
                    master_product_id=master.get('id') if master else None,
                    detected_count=1, confirmed_count=1, unit='pcs',
                    detected_barcode=value,
                    barcode_confidence=confidence,
                    bounding_box=bbox, frame_number=frame_number,
                    detected_product_name=master.get('product_name', '') if master else '',
                    confirmation_status='pending',
                )
                new_items += 1
        else:
            DetectedItem.objects.create(
                session=session, store=store,
                detection_method='barcode',
                confidence_score=confidence,
                detected_count=1, confirmed_count=1, unit='pcs',
                detected_barcode=value,
                barcode_confidence=confidence,
                bounding_box=bbox, frame_number=frame_number,
                confirmation_status='pending',
                user_notes='Barcode tidak ditemukan di database.',
            )
            new_items += 1

    session.frame_count += 1
    session.total_items_detected = DetectedItem.objects.filter(
        session=session, confirmation_status='pending'
    ).count()
    session.save(update_fields=['frame_count', 'total_items_detected', 'updated_at'])

    return {
        'matched': matched,
        'new_items': new_items,
        'errors': errors,
        'new_master_products': new_master_products,
    }


def process_bulk_barcodes(session, barcode_batches):
    """
    Process bulk barcode scan — multiple shelves/products in one request.
    Each entry: {barcode, count, batch_number, expiry_date}
    """
    store = session.store
    total_items = 0
    matched = 0
    new_items = 0

    for entry in barcode_batches:
        value = entry.get('barcode', '').strip()
        count = int(entry.get('count', 1))
        batch_number = entry.get('batch_number', '')
        expiry_date = entry.get('expiry_date', '')

        if not value:
            continue

        lookup_result = lookup_barcode(value, store=store)
        master = lookup_result.get('master_product') if lookup_result.get('found') else None

        expiry_parsed = None
        if expiry_date:
            try:
                from datetime import date
                expiry_parsed = date.fromisoformat(expiry_date)
            except (ValueError, TypeError):
                pass

        DetectedItem.objects.create(
            session=session, store=store,
            detection_method='barcode',
            confidence_score=0.95,
            master_product_id=master.get('id') if master else None,
            detected_count=count, confirmed_count=count, unit='pcs',
            detected_barcode=value,
            barcode_confidence=0.95,
            detected_batch_number=batch_number,
            detected_expiry_date=expiry_parsed,
            frame_number=0,
            detected_product_name=master.get('product_name', '') if master else '',
            confirmation_status='pending',
        )

        total_items += count
        if master:
            matched += 1
        else:
            new_items += 1

    session.total_items_detected = DetectedItem.objects.filter(
        session=session, confirmation_status='pending'
    ).count()
    session.save(update_fields=['total_items_detected', 'updated_at'])

    return {'total_items': total_items, 'matched': matched, 'new_items': new_items}
