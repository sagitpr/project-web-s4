"""
FEFO (First Expired First Out) inventory engine.
Picks the nearest-expiring batch first when processing stock outbound.

Core functions:
- get_fefo_batch(store, master_product, quantity) — pick best batch
- stock_in(store, master_product, batch_number, ...) — record inbound
- stock_out(store, master_product, quantity, reference) — record outbound
- get_expiry_summary(store) — expiry dashboard data
"""

import logging
from decimal import Decimal
from datetime import timedelta

from django.db import transaction as db_transaction
from django.db.models import Sum, Q
from django.utils import timezone

from ..models import MasterProduct, ProductBatch, InventoryStock

logger = logging.getLogger('django_backend.inventory.fefo')


def get_fefo_batch(store, master_product, quantity):
    """
    FEFO: Get the best batch to pick from for a given quantity.
    
    Rules:
    1. Only fresh/non-expired batches (status = 'fresh' or 'expiring_soon')
    2. Sort by expiry_date ASC (nearest expiry first)
    3. Pick from multiple batches if needed to fulfill quantity
    
    Returns:
        list of dicts: [{'batch': ProductBatch, 'pick_qty': Decimal}, ...]
    """
    batches = ProductBatch.objects.filter(
        store=store,
        master_product=master_product,
        status__in=['fresh', 'expiring_soon'],
        current_quantity__gt=0,
        is_active=True,
    ).order_by('expiry_date', 'batch_number')

    picks = []
    remaining = Decimal(str(quantity))

    for batch in batches:
        if remaining <= 0:
            break
        available = batch.current_quantity
        pick_qty = min(remaining, available)
        if pick_qty > 0:
            picks.append({
                'batch': batch,
                'pick_qty': pick_qty,
            })
            remaining -= pick_qty

    if remaining > 0:
        return {
            'success': False,
            'picks': picks,
            'error': f'Stok tidak mencukupi. Dibutuhkan {quantity}, tersedia {Decimal(str(quantity)) - remaining}.',
            'shortage': float(remaining),
        }

    return {
        'success': True,
        'picks': picks,
        'total_picked': float(quantity),
    }


def get_fefo_batch_simple(store_id, master_product_id, quantity):
    """Simple wrapper for API views — converts IDs to instances."""
    from stores.models import Store
    store = Store.objects.get(id=store_id)
    master_product = MasterProduct.objects.get(id=master_product_id)
    return get_fefo_batch(store, master_product, quantity)


@db_transaction.atomic
def stock_in(
    store,
    master_product,
    batch_number,
    production_date,
    expiry_date,
    quantity,
    unit='pcs',
    purchase_price=None,
    product=None,
    notes='',
    created_by=None,
    reference_type='',
    reference_id='',
):
    """
    Record stock inbound: creates/updates batch and logs transaction.
    
    If a batch with the same batch_number + master_product + store exists,
    it adds to existing quantity instead of creating duplicate.
    
    Returns:
        dict with batch, transaction, and status
    """
    # Find or create batch
    batch, created = ProductBatch.objects.get_or_create(
        store=store,
        master_product=master_product,
        batch_number=batch_number,
        defaults={
            'product': product,
            'production_date': production_date,
            'expiry_date': expiry_date,
            'initial_quantity': quantity,
            'current_quantity': quantity,
            'unit': unit,
            'purchase_price': purchase_price,
            'notes': notes,
        }
    )

    if not created:
        # Add to existing batch
        batch.initial_quantity += quantity
        batch.current_quantity += quantity
        if purchase_price:
            # Weighted average purchase price
            total_cost = (batch.purchase_price * batch.initial_quantity) + (purchase_price * quantity)
            batch.purchase_price = total_cost / (batch.initial_quantity + quantity)
        batch.save(update_fields=['initial_quantity', 'current_quantity', 'purchase_price', 'updated_at'])
        batch.refresh_status()

    # Log transaction
    qty_before = batch.current_quantity - quantity
    transaction = InventoryStock.objects.create(
        store=store,
        master_product=master_product,
        product=product,
        batch=batch,
        transaction_type='stock_in',
        quantity=quantity,
        quantity_before=qty_before,
        quantity_after=batch.current_quantity,
        notes=notes,
        created_by=created_by,
        reference_type=reference_type,
        reference_id=reference_id,
    )

    # Sync Product.stock for full Warungio integration
    if product:
        _sync_product_stock(product)
    elif batch.product:
        _sync_product_stock(batch.product)

    return {
        'success': True,
        'batch': batch,
        'transaction': transaction,
        'is_new_batch': created,
    }


@db_transaction.atomic
def stock_out(
    store,
    master_product,
    quantity,
    notes='',
    created_by=None,
    reference_type='',
    reference_id='',
):
    """
    Record stock outbound using FEFO (pick nearest-expiring batch first).
    
    Returns:
        dict with picks, transactions, and status
    """
    # FEFO: get best batch to pick from
    fefo_result = get_fefo_batch(store, master_product, quantity)

    if not fefo_result['success']:
        return fefo_result

    transactions = []
    total_qty = Decimal('0')

    for pick in fefo_result['picks']:
        batch = pick['batch']
        pick_qty = pick['pick_qty']
        qty_before = batch.current_quantity

        # Deduct from batch
        batch.current_quantity -= pick_qty
        batch.refresh_status()
        batch.save(update_fields=['current_quantity', 'status', 'updated_at'])

        # Log transaction
        txn = InventoryStock.objects.create(
            store=store,
            master_product=master_product,
            batch=batch,
            transaction_type='stock_out',
            quantity=pick_qty,
            quantity_before=qty_before,
            quantity_after=batch.current_quantity,
            notes=notes,
            created_by=created_by,
            reference_type=reference_type,
            reference_id=reference_id,
        )
        transactions.append({
            'transaction_id': txn.id,
            'batch_id': batch.id,
            'batch_number': batch.batch_number,
            'expiry_date': batch.expiry_date.isoformat(),
            'quantity': float(pick_qty),
        })
        total_qty += pick_qty

    # Sync Product.stock for all affected batches that have a linked Product listing
    synced_products = set()
    for pick in fefo_result['picks']:
        batch = pick['batch']
        if batch.product and batch.product.id not in synced_products:
            _sync_product_stock(batch.product)
            synced_products.add(batch.product.id)

    return {
        'success': True,
        'total_quantity': float(total_qty),
        'batches_used': len(transactions),
        'transactions': transactions,
        'note': 'FEFO: Picked nearest-expiring batch first.',
    }


def get_batch_summary(store, master_product=None):
    """
    Get summary of all active batches for a store.
    
    Returns grouped by status: fresh, expiring_soon, expired
    """
    qs = ProductBatch.objects.filter(
        store=store, is_active=True
    ).select_related('master_product')

    if master_product:
        qs = qs.filter(master_product=master_product)

    summary = {
        'total_batches': qs.count(),
        'total_stock_qty': qs.aggregate(
            total=Sum('current_quantity')
        )['total'] or 0,
    }

    for status in ['fresh', 'expiring_soon', 'expired', 'disposed']:
        status_qs = qs.filter(status=status)
        count = status_qs.count()
        qty = status_qs.aggregate(
            total=Sum('current_quantity')
        )['total'] or 0
        summary[f'{status}_count'] = count
        summary[f'{status}_qty'] = float(qty)

    return summary


def _sync_product_stock(product):
    """
    Sync the Product.stock field with total batch quantities.
    Called after stock_in or stock_out to keep Product.stock in sync.
    
    The Product.stock is auto-calculated as the sum of current_quantity
    across all active, non-expired batches linked to this product.
    """
    if not product:
        return
    
    from django.db.models import Sum
    total = ProductBatch.objects.filter(
        product=product,
        is_active=True,
        status__in=['fresh', 'expiring_soon'],
    ).aggregate(
        total=Sum('current_quantity')
    )['total'] or 0
    
    product.stock = int(total)
    product.save(update_fields=['stock', 'updated_at'])


def get_expiry_summary(store):
    """
    Get expiry dashboard data for a store.
    Returns counts and lists of expiring/expired batches.
    """
    today = timezone.now().date()
    next_week = today + timedelta(days=7)
    next_month = today + timedelta(days=30)

    expiring_this_week = ProductBatch.objects.filter(
        store=store, is_active=True,
        expiry_date__range=[today, next_week],
        status__in=['fresh', 'expiring_soon'],
    ).select_related('master_product').order_by('expiry_date')

    expiring_this_month = ProductBatch.objects.filter(
        store=store, is_active=True,
        expiry_date__range=[today, next_month],
        status__in=['fresh', 'expiring_soon'],
    ).exclude(id__in=expiring_this_week.values('id'))

    already_expired = ProductBatch.objects.filter(
        store=store, is_active=True,
        status='expired',
    ).select_related('master_product').order_by('expiry_date')

    return {
        'store_id': store.id,
        'today': today.isoformat(),
        'expiring_this_week_count': expiring_this_week.count(),
        'expiring_this_month_count': expiring_this_month.count(),
        'already_expired_count': already_expired.count(),
        'expiring_this_week': [
            {
                'id': b.id,
                'product_name': b.master_product.product_name,
                'product_id': b.master_product.id,
                'barcode': b.master_product.barcode,
                'batch_number': b.batch_number,
                'expiry_date': b.expiry_date.isoformat(),
                'days_until_expiry': (b.expiry_date - today).days,
                'current_quantity': float(b.current_quantity),
                'unit': b.unit,
                'shelf_life_remaining_pct': float(b.shelf_life_remaining_pct),
            }
            for b in expiring_this_week
        ],
        'already_expired': [
            {
                'id': b.id,
                'product_name': b.master_product.product_name,
                'product_id': b.master_product.id,
                'barcode': b.master_product.barcode,
                'batch_number': b.batch_number,
                'expiry_date': b.expiry_date.isoformat(),
                'days_overdue': (today - b.expiry_date).days,
                'current_quantity': float(b.current_quantity),
                'unit': b.unit,
            }
            for b in already_expired
        ],
    }
