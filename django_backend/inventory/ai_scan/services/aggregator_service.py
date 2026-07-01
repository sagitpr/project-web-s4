"""
Scan Aggregator Service for AI Smart Inventory Scanning.

Combines results from Object Detection, OCR, and Barcode Recognition
into structured scan results for seller review before saving.

Core functions:
- aggregate_scan_results() — combine all detections into review-ready format
- confirm_and_save_items() — save confirmed items as inventory batches
- register_new_product() — create MasterProduct from scan data
- get_scan_summary() — session-level summary for dashboard
"""

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from ...models import MasterProduct, ProductBatch, SmartScanSession, DetectedItem
from inventory.services.fefo_engine import stock_in
from inventory.services.barcode_lookup import lookup_barcode
from inventory.services.expiry_service import check_and_notify_expiry

logger = logging.getLogger('django_backend.inventory.ai_scan.aggregator')


def aggregate_scan_results(session):
    """
    Consolidate all detections in a session into a review-ready list.
    Grouped by product with merged confidence, count, and source data.
    """
    items = DetectedItem.objects.filter(
        session=session,
    ).select_related('master_product').order_by('-confidence_score')

    if not items.exists():
        return {
            'session_id': session.id,
            'status': session.status,
            'items': [],
            'summary': {'total_items': 0, 'matched_to_master': 0, 'unmatched': 0, 'avg_confidence': 0},
        }

    groups = {}
    for item in items:
        key = item.master_product_id
        if key:
            key = f'master_{key}'
        elif item.detected_barcode:
            key = f'barcode_{item.detected_barcode}'
        else:
            key = f'detected_{item.detected_product_name.lower()}'

        if key in groups:
            g = groups[key]
            g['total_count'] += item.detected_count
            g['confirmed_count'] += item.confirmed_count
            g['confidence'] = max(g['confidence'], float(item.confidence_score))
            g['item_ids'].append(item.id)
            if item.detected_barcode and not g.get('barcode'):
                g['barcode'] = item.detected_barcode
            if item.detected_batch_number and not g.get('batch_number'):
                g['batch_number'] = item.detected_batch_number
            if item.detected_expiry_date and not g.get('expiry_date'):
                g['expiry_date'] = item.detected_expiry_date.isoformat()
        else:
            groups[key] = {
                'item_ids': [item.id],
                'master_product_id': item.master_product_id,
                'master_product_name': (
                    item.master_product.product_name if item.master_product
                    else item.detected_product_name
                ),
                'barcode': item.detected_barcode,
                'brand': item.master_product.brand if item.master_product else item.detected_brand,
                'unit': item.unit,
                'total_count': item.detected_count,
                'confirmed_count': item.confirmed_count or item.detected_count,
                'confidence': float(item.confidence_score),
                'batch_number': item.detected_batch_number,
                'expiry_date': (
                    item.detected_expiry_date.isoformat()
                    if item.detected_expiry_date else None
                ),
                'detection_methods': [item.detection_method],
                'status': item.confirmation_status,
            }

    items_list = list(groups.values())
    matched = sum(1 for g in items_list if g['master_product_id'])
    unmatched = len(items_list) - matched
    avg_c = round(
        sum(g['confidence'] for g in items_list) / len(items_list), 2
    ) if items_list else 0

    return {
        'session_id': session.id,
        'status': session.status,
        'scan_mode': session.scan_mode,
        'items': items_list,
        'summary': {
            'total_items': len(items_list),
            'matched_to_master': matched,
            'unmatched': unmatched,
            'avg_confidence': avg_c,
        },
    }


@transaction.atomic
def confirm_and_save_items(session, confirmed_items, user):
    """
    Save confirmed detected items as inventory batches via FEFO stock_in.
    Triggers expiry notifications after batch creation.
    """
    store = session.store
    batches_created = []
    errors = []
    today = timezone.now().date()

    for entry in confirmed_items:
        item_id = entry.get('item_id')
        if not item_id:
            errors.append({'error': 'item_id wajib diisi.'})
            continue

        try:
            item = DetectedItem.objects.get(id=item_id, session=session, store=store)
        except DetectedItem.DoesNotExist:
            errors.append({'error': f'Item {item_id} tidak ditemukan.'})
            continue

        if not item.master_product:
            errors.append({
                'item_id': item_id,
                'error': 'Produk tidak terdaftar di Master Product Database. Daftarkan terlebih dahulu.',
            })
            continue

        confirmed_qty = Decimal(str(
            entry.get('confirmed_count', item.confirmed_count or item.detected_count)
        ))
        batch_number = entry.get(
            'batch_number',
            item.detected_batch_number or f'AUTO-{datetime.now().strftime("%Y%m%d%H%M%S")}'
        )
        expiry_str = entry.get(
            'expiry_date',
            item.detected_expiry_date.isoformat() if item.detected_expiry_date else None
        )
        unit = entry.get('unit', item.unit)
        notes = entry.get('notes', item.user_notes)

        expiry_date = None
        production_date = today - timedelta(days=30)

        if expiry_str:
            try:
                expiry_date = date.fromisoformat(expiry_str)
            except (ValueError, TypeError):
                pass

        if not expiry_date:
            expiry_date = today + timedelta(days=730)

        if expiry_date <= production_date:
            production_date = expiry_date - timedelta(days=30)

        result = stock_in(
            store=store,
            master_product=item.master_product,
            batch_number=batch_number,
            production_date=production_date,
            expiry_date=expiry_date,
            quantity=confirmed_qty,
            unit=unit,
            notes=f'AI Scan: {notes}' if notes else 'AI Scan: Smart Inventory Scan',
            created_by=user,
            reference_type='ai_scan',
            reference_id=str(session.id),
        )

        if result['success']:
            item.confirmed_count = int(confirmed_qty)
            item.confirmation_status = 'accepted'
            item.created_batch = result['batch']
            item.confirmed_at = timezone.now()
            item.user_notes = notes
            item.save(update_fields=[
                'confirmed_count', 'confirmation_status', 'created_batch',
                'confirmed_at', 'user_notes', 'updated_at',
            ])

            batches_created.append({
                'item_id': item.id,
                'batch_id': result['batch'].id,
                'master_product_id': item.master_product.id,
                'product_name': item.master_product.product_name,
                'batch_number': batch_number,
                'quantity': float(confirmed_qty),
                'unit': unit,
                'expiry_date': expiry_date.isoformat(),
                'shelf_life_days': result['batch'].shelf_life_days,
                'status': result['batch'].status,
            })
        else:
            errors.append({'item_id': item_id, 'error': 'Gagal membuat batch.'})

    session.total_items_confirmed = DetectedItem.objects.filter(
        session=session,
        confirmation_status__in=['accepted', 'corrected'],
    ).count()
    session.total_batches_created = len(batches_created)

    if batches_created:
        session.status = 'saved'
        session.completed_at = timezone.now()
        # Trigger expiry notifications for newly created batches
        try:
            check_and_notify_expiry(store)
        except Exception as e:
            logger.warning('Expiry notification error after AI scan save: %s', e)

    session.save(update_fields=[
        'total_items_confirmed', 'total_batches_created',
        'status', 'completed_at', 'updated_at',
    ])

    return {
        'success': len(errors) == 0,
        'batches_created': batches_created,
        'total_batches': len(batches_created),
        'total_items_confirmed': session.total_items_confirmed,
        'errors': errors if errors else None,
    }


@transaction.atomic
def register_new_product(session, product_data, user):
    """Register a new MasterProduct from scan data when barcode is not found."""
    barcode = product_data.get('barcode', '').strip()
    if not barcode:
        return {'success': False, 'error': 'Barcode wajib diisi.'}

    existing = MasterProduct.objects.filter(barcode=barcode).first()
    if existing:
        return {
            'success': True,
            'master_product': {
                'id': existing.id, 'barcode': existing.barcode,
                'product_name': existing.product_name,
                'brand': existing.brand, 'category': existing.category,
            },
            'note': 'Produk sudah terdaftar.',
        }

    master = MasterProduct.objects.create(
        barcode=barcode,
        product_name=product_data.get('product_name', 'Produk Baru')[:200],
        brand=product_data.get('brand', '')[:100],
        category=product_data.get('category', 'Umum')[:100],
        subcategory=product_data.get('subcategory', '')[:100],
        unit=product_data.get('unit', 'pcs'),
        weight_value=product_data.get('weight_value'),
        weight_unit=product_data.get('weight_unit', ''),
        image_url=product_data.get('image_url', ''),
        manufacturer=product_data.get('manufacturer', '')[:200],
        bpom_number=product_data.get('bpom_number', ''),
    )

    logger.info('AI Scan registered new MasterProduct %s (%s)', master.barcode, master.product_name)

    return {
        'success': True,
        'master_product': {
            'id': master.id, 'barcode': master.barcode,
            'product_name': master.product_name, 'brand': master.brand,
            'category': master.category, 'unit': master.unit,
            'weight_value': float(master.weight_value) if master.weight_value else None,
            'weight_unit': master.weight_unit,
            'manufacturer': master.manufacturer,
            'bpom_number': master.bpom_number,
        },
    }


@transaction.atomic
def update_detected_item(item_id, update_data):
    """Update a detected item's data (user correction before saving)."""
    try:
        item = DetectedItem.objects.get(id=item_id)
    except DetectedItem.DoesNotExist:
        return {'success': False, 'error': 'Item tidak ditemukan.'}

    fields = []
    if 'confirmed_count' in update_data:
        item.confirmed_count = int(update_data['confirmed_count'])
        fields.append('confirmed_count')
    if 'batch_number' in update_data:
        item.detected_batch_number = update_data['batch_number']
        fields.append('detected_batch_number')
    if 'expiry_date' in update_data and update_data['expiry_date']:
        try:
            item.detected_expiry_date = date.fromisoformat(update_data['expiry_date'])
            fields.append('detected_expiry_date')
        except (ValueError, TypeError):
            pass
    if 'unit' in update_data:
        item.unit = update_data['unit']
        fields.append('unit')
    if 'master_product_id' in update_data:
        try:
            mp = MasterProduct.objects.get(id=int(update_data['master_product_id']))
            item.master_product = mp
            fields.append('master_product')
        except (ValueError, MasterProduct.DoesNotExist):
            pass
    if 'notes' in update_data:
        item.user_notes = update_data['notes']
        fields.append('user_notes')
    if 'confirmation_status' in update_data:
        item.confirmation_status = update_data['confirmation_status']
        fields.append('confirmation_status')

    if fields:
        fields.append('updated_at')
        item.save(update_fields=fields)

    return {
        'success': True,
        'item': {
            'id': item.id,
            'master_product_id': item.master_product_id,
            'product_name': item.master_product.product_name if item.master_product else item.detected_product_name,
            'detected_count': item.detected_count,
            'confirmed_count': item.confirmed_count,
            'batch_number': item.detected_batch_number,
            'expiry_date': item.detected_expiry_date.isoformat() if item.detected_expiry_date else None,
            'unit': item.unit,
        },
    }


def get_scan_summary(store, user=None, days=7):
    """Get AI scan summary for the seller's dashboard."""
    from django.db.models import Sum, Avg
    since = timezone.now() - timedelta(days=days)
    sessions = SmartScanSession.objects.filter(store=store, started_at__gte=since)

    total = sessions.count()
    completed = sessions.filter(status='saved').count()
    detected = sessions.aggregate(total=Sum('total_items_detected'))['total'] or 0
    confirmed = sessions.aggregate(total=Sum('total_items_confirmed'))['total'] or 0
    batches = sessions.aggregate(total=Sum('total_batches_created'))['total'] or 0

    return {
        'store_id': store.id,
        'period_days': days,
        'sessions': {'total': total, 'completed': completed},
        'items': {'detected': detected, 'confirmed': confirmed, 'pending_review': detected - confirmed},
        'batches_created': batches,
        'avg_items_per_session': round(detected / total, 1) if total > 0 else 0,
    }


def match_unmatched_items(session):
    """Try to match pending items without a master_product by barcode or name."""
    unmatched = DetectedItem.objects.filter(
        session=session, master_product__isnull=True, confirmation_status='pending',
    )
    matched = 0
    for item in unmatched:
        if item.detected_barcode:
            result = lookup_barcode(item.detected_barcode)
            mid = result.get('master_product', {}).get('id') if result.get('found') else None
            if mid:
                item.master_product = MasterProduct.objects.get(id=mid)
                item.save(update_fields=['master_product', 'updated_at'])
                matched += 1
                continue
        if item.detected_product_name:
            mp = MasterProduct.objects.filter(
                product_name__icontains=item.detected_product_name, is_active=True,
            ).first()
            if mp:
                item.master_product = mp
                item.save(update_fields=['master_product', 'updated_at'])
                matched += 1
    remaining = DetectedItem.objects.filter(
        session=session, master_product__isnull=True, confirmation_status='pending',
    ).count()
    return {'matched': matched, 'remaining': remaining}
