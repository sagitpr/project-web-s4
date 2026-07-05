"""
Wallet Service — atomic balance operations for Dompet Warungio.

All balance changes MUST go through this service to ensure:
- Row-level locking via select_for_update (prevents race conditions)
- Balance never goes negative (validated)
- Every mutation creates a WalletTransaction record (audit trail)
- Double-update protection via idempotency key
"""

import logging
from decimal import Decimal
from django.db import transaction
from django.db.models import F
from ..models import Wallet, WalletTransaction

logger = logging.getLogger(__name__)


class WalletError(Exception):
    """Base exception for wallet operations."""
    pass


class InsufficientBalanceError(WalletError):
    """Raised when wallet balance is insufficient."""
    pass


class DuplicateTransactionError(WalletError):
    """Raised when a duplicate transaction is detected."""
    pass


@transaction.atomic
def get_wallet(user, lock=False):
    """
    Get or create a wallet for the given user.
    
    Migrates legacy balance from user.device_info['wallet_balance']
    on first creation to prevent data loss for existing users.
    
    Args:
        user: User instance
        lock: If True, acquire row-level lock (select_for_update)
    
    Returns:
        Wallet instance
    """
    if lock:
        wallet = Wallet.objects.select_for_update().filter(user=user).first()
        if wallet:
            return wallet
        # Wallet doesn't exist yet — create it atomically
        # Check if user has legacy balance in device_info
        legacy_balance = _get_legacy_balance(user)
        wallet = Wallet.objects.create(user=user, balance=legacy_balance)
        # Re-fetch with lock
        return Wallet.objects.select_for_update().get(user=user)
    
    wallet, created = Wallet.objects.get_or_create(user=user, defaults={'balance': Decimal('0')})
    if created:
        # Migrate legacy balance from device_info
        legacy_balance = _get_legacy_balance(user)
        if legacy_balance > 0:
            wallet.balance = legacy_balance
            wallet.save(update_fields=['balance'])
            logger.info('Migrated wallet balance for %s: Rp %s', user.email, legacy_balance)
    return wallet


def _get_legacy_balance(user):
    """Check device_info for legacy wallet_balance and return it."""
    if user.device_info and isinstance(user.device_info, dict):
        legacy = user.device_info.get('wallet_balance')
        if legacy is not None:
            try:
                return Decimal(str(legacy))
            except (ValueError, TypeError):
                pass
    return Decimal('0')


@transaction.atomic
def credit_wallet(user, amount, tx_type='topup', description=None,
                  reference_type=None, reference_id=None, idempotency_key=None):
    """
    Add funds to a user's wallet atomically.
    
    Args:
        user: User instance
        amount: Decimal or float — amount to credit
        tx_type: Transaction type (topup, refund, bonus, adjustment)
        description: Optional description
        reference_type: Optional reference type (e.g., 'midtrans', 'order')
        reference_id: Optional reference ID
        idempotency_key: If provided, skip if a transaction with this
                         reference_type + reference_id already exists
    
    Returns:
        dict with success status and wallet balance info
    
    Raises:
        DuplicateTransactionError: If idempotency check fails
        WalletError: On other errors
    """
    amount = Decimal(str(amount))
    if amount <= 0:
        raise WalletError("Amount must be positive for credit.")
    
    # Idempotency check
    if idempotency_key or (reference_type and reference_id):
        existing = WalletTransaction.objects.filter(
            reference_type=reference_type or idempotency_key,
            reference_id=reference_id or idempotency_key,
            tx_type=tx_type,
        ).first()
        if existing:
            logger.info(
                'Duplicate wallet credit blocked: user=%s, ref=%s/%s, amount=%s',
                user.email, reference_type, reference_id, amount
            )
            return {
                'success': True,
                'duplicate': True,
                'balance_before': existing.balance_before,
                'balance_after': existing.balance_after,
                'transaction': existing,
            }
    
    wallet = get_wallet(user, lock=True)
    balance_before = wallet.balance
    balance_after = balance_before + amount
    
    wallet.balance = balance_after
    wallet.save(update_fields=['balance', 'updated_at'])
    
    tx = WalletTransaction.objects.create(
        wallet=wallet,
        user=user,
        tx_type=tx_type,
        amount=amount,
        balance_before=balance_before,
        balance_after=balance_after,
        description=description,
        reference_type=reference_type,
        reference_id=reference_id,
    )
    
    logger.info(
        'Wallet credited: user=%s, amount=%s, balance=%s→%s, type=%s/%s',
        user.email, amount, balance_before, balance_after, reference_type, reference_id
    )
    
    return {
        'success': True,
        'balance_before': balance_before,
        'balance_after': balance_after,
        'transaction': tx,
    }


@transaction.atomic
def debit_wallet(user, amount, tx_type='payment', description=None,
                 reference_type=None, reference_id=None, idempotency_key=None):
    """
    Deduct funds from a user's wallet atomically.
    
    Args:
        user: User instance
        amount: Decimal or float — amount to debit
        tx_type: Transaction type (payment, withdrawal)
        description: Optional description
        reference_type: Optional reference type
        reference_id: Optional reference ID
        idempotency_key: If provided, skip if duplicate
    
    Returns:
        dict with success status and wallet balance info
    
    Raises:
        InsufficientBalanceError: If balance < amount
        DuplicateTransactionError: If idempotency check fails
        WalletError: On other errors
    """
    amount = Decimal(str(amount))
    if amount <= 0:
        raise WalletError("Amount must be positive for debit.")
    
    # Idempotency check
    if idempotency_key or (reference_type and reference_id):
        existing = WalletTransaction.objects.filter(
            reference_type=reference_type or idempotency_key,
            reference_id=reference_id or idempotency_key,
            tx_type=tx_type,
        ).first()
        if existing:
            logger.info(
                'Duplicate wallet debit blocked: user=%s, ref=%s/%s, amount=%s',
                user.email, reference_type, reference_id, amount
            )
            return {
                'success': True,
                'duplicate': True,
                'balance_before': existing.balance_before,
                'balance_after': existing.balance_after,
                'transaction': existing,
            }
    
    wallet = get_wallet(user, lock=True)
    
    if wallet.balance < amount:
        raise InsufficientBalanceError(
            f"Saldo tidak mencukupi. Tersedia: Rp {wallet.balance}, dibutuhkan: Rp {amount}"
        )
    
    balance_before = wallet.balance
    balance_after = balance_before - amount
    
    wallet.balance = balance_after
    wallet.save(update_fields=['balance', 'updated_at'])
    
    tx = WalletTransaction.objects.create(
        wallet=wallet,
        user=user,
        tx_type=tx_type,
        amount=-amount,  # Negative amount for debits
        balance_before=balance_before,
        balance_after=balance_after,
        description=description,
        reference_type=reference_type,
        reference_id=reference_id,
    )
    
    logger.info(
        'Wallet debited: user=%s, amount=%s, balance=%s→%s, type=%s/%s',
        user.email, amount, balance_before, balance_after, reference_type, reference_id
    )
    
    return {
        'success': True,
        'balance_before': balance_before,
        'balance_after': balance_after,
        'transaction': tx,
    }


def get_balance(user):
    """Get the current wallet balance for a user (no lock)."""
    wallet = get_wallet(user, lock=False)
    return wallet.balance


def get_transactions(user, limit=20):
    """Get recent wallet transactions for a user."""
    return WalletTransaction.objects.filter(
        user=user
    ).select_related('wallet').order_by('-created_at')[:limit]


def get_transactions_paginated(user, page=1, page_size=10, tx_type=None):
    """Get paginated wallet transactions for a user."""
    qs = WalletTransaction.objects.filter(user=user)
    if tx_type and tx_type != 'all':
        qs = qs.filter(tx_type=tx_type)
    
    total = qs.count()
    start = (page - 1) * page_size
    end = start + page_size
    transactions = qs.order_by('-created_at')[start:end]
    
    return {
        'count': total,
        'results': [{
            'id': t.id,
            'tx_type': t.tx_type,
            'tx_type_label': t.get_tx_type_display(),
            'amount': float(t.amount),
            'balance_before': float(t.balance_before),
            'balance_after': float(t.balance_after),
            'description': t.description,
            'reference_type': t.reference_type,
            'reference_id': t.reference_id,
            'created_at': t.created_at.isoformat(),
        } for t in transactions],
        'page': page,
        'page_size': page_size,
    }
