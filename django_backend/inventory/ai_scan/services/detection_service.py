"""
AI Object Detection Service for Smart Inventory Scanning.

Simulates server-side processing of object detection results sent by the
Flutter camera app (which runs on-device ML). In production, this would
integrate with TensorFlow Lite / MLKit / YOLO outputs.

Handles:
- Multiple product detection per frame
- Identical item counting (including stacks, hanging items, shelves)
- Deduplication across frames
- Confidence scoring
- Detection metadata extraction
"""

import logging

from ...models import SmartScanSession, DetectedItem

logger = logging.getLogger('django_backend.inventory.ai_scan.detection')


def process_frame_detections(session, detections, frame_number=0):
    """
    Process object detection results from a single camera frame.
    
    Args:
        session: SmartScanSession instance
        detections: list of dicts, each containing:
            - label: str (detected object label)
            - confidence: float (0-1)
            - bbox: dict {x, y, width, height} (optional)
            - features: dict (optional visual features)
        frame_number: int
    
    Returns:
        dict with counts of new vs matched items
    """
    store = session.store
    new_count = 0
    matched_count = 0

    for detection in detections:
        label = detection.get('label', '').lower()
        confidence = min(float(detection.get('confidence', 0.5)), 1.0)
        bbox = detection.get('bbox')
        features = detection.get('features', {})

        product_match = _match_label_to_masterproduct(label)
        item_count = _estimate_item_count(detection, features)
        existing = _find_recent_duplicate(session, label, confidence)

        if existing:
            existing.detected_count += item_count
            existing.confidence_score = max(existing.confidence_score, confidence)
            if bbox:
                existing.bounding_box = bbox
            existing.save(update_fields=[
                'detected_count', 'confidence_score', 'bounding_box', 'updated_at',
            ])
            matched_count += 1
        else:
            DetectedItem.objects.create(
                session=session,
                store=store,
                detection_method='object_detection',
                confidence_score=confidence,
                master_product=product_match,
                detected_count=item_count,
                confirmed_count=item_count,
                unit='pcs',
                bounding_box=bbox,
                detection_features=features,
                frame_number=frame_number,
                detected_product_name=label.title(),
                confirmation_status='pending',
            )
            new_count += 1

    session.frame_count += 1
    session.total_items_detected = DetectedItem.objects.filter(
        session=session, confirmation_status='pending'
    ).count()
    session.save(update_fields=[
        'frame_count', 'total_items_detected', 'updated_at',
    ])

    return {
        'new_items': new_count,
        'matched_items': matched_count,
        'total_detected_in_frame': len(detections),
    }


def _match_label_to_masterproduct(label):
    """Try to match a detected label to an existing MasterProduct."""
    from ...models import MasterProduct
    from django.db.models import Q

    product = MasterProduct.objects.filter(
        product_name__iexact=label, is_active=True,
    ).first()
    if product:
        return product

    words = [w for w in label.split() if len(w) >= 3]
    for word in words:
        product = MasterProduct.objects.filter(
            Q(product_name__icontains=word) | Q(brand__icontains=word),
            is_active=True,
        ).first()
        if product:
            return product

    return None


def _estimate_item_count(detection, features=None):
    """Estimate item count from visual features (stacks, hanging, shelves, boxes)."""
    features = features or {}
    stack = int(features.get('stack_count', 0))
    hanging = int(features.get('hanging_count', 0))
    shelf = int(features.get('shelf_count', 0))
    box = int(features.get('box_count', 0))

    if stack:
        return stack
    if hanging:
        return hanging
    if shelf:
        return shelf
    if box > 1:
        return box
    return 1


def _find_recent_duplicate(session, label, confidence):
    """Check if this product was already detected in a recent frame."""
    recent = DetectedItem.objects.filter(
        session=session,
        detected_product_name__iexact=label,
        confirmation_status='pending',
    ).order_by('-detected_at').first()

    if recent and (
        recent.frame_number == 0
        or abs(recent.frame_number - session.frame_count) <= 3
    ):
        return recent
    return None


def aggregate_session_detections(session):
    """
    Aggregate all pending detections in a session.
    Groups identical products, returns consolidated list for review.
    """
    items = DetectedItem.objects.filter(
        session=session,
        confirmation_status='pending',
    ).order_by('-confidence_score')

    if not items.exists():
        return []

    groups = {}
    for item in items:
        key = item.master_product_id or item.detected_product_name.lower()
        if key in groups:
            g = groups[key]
            g['count'] += item.detected_count
            g['confidence'] = max(g['confidence'], float(item.confidence_score))
            g['items'].append(item.id)
        else:
            groups[key] = {
                'master_product_id': item.master_product_id,
                'master_product_name': (
                    item.master_product.product_name
                    if item.master_product else item.detected_product_name
                ),
                'detected_barcode': item.detected_barcode,
                'detected_batch': item.detected_batch_number,
                'detected_expiry': (
                    item.detected_expiry_date.isoformat()
                    if item.detected_expiry_date else None
                ),
                'count': item.detected_count,
                'unit': item.unit,
                'confidence': float(item.confidence_score),
                'items': [item.id],
                'detection_methods': [item.detection_method],
            }

    return list(groups.values())


def deduplicate_session(session):
    """Merge duplicate detections into single items."""
    items = DetectedItem.objects.filter(
        session=session,
        confirmation_status='pending',
    ).order_by('-confidence_score')

    seen = {}
    to_delete = []

    for item in items:
        key = item.master_product_id or item.detected_product_name.lower()
        if not key:
            continue
        if key in seen:
            primary = seen[key]
            primary.detected_count += item.detected_count
            primary.confidence_score = max(
                primary.confidence_score, item.confidence_score
            )
            primary.save(update_fields=[
                'detected_count', 'confidence_score', 'updated_at',
            ])
            to_delete.append(item.id)
        else:
            seen[key] = item

    if to_delete:
        DetectedItem.objects.filter(id__in=to_delete).delete()

    return {'merged': len(seen), 'removed_duplicates': len(to_delete)}
