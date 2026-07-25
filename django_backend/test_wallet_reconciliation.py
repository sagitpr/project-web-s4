"""
Wallet & Financial Reconciliation Test for Warungio Marketplace.

Verifies:
  - Wallet credit/debit operations are atomic and consistent
  - Admin fees are recorded correctly per transaction
  - Duplicate transaction prevention via idempotency keys
  - Wallet balance never goes negative
  - Balance consistency after multiple transactions
  - Settlement/cash flow integrity

Run with:  python -m pytest django_backend/test_wallet_reconciliation.py -v --tb=long
"""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Sum

from payments.models import Wallet, WalletTransaction, AdminFeeTransaction, Payment as PaymentModel
from payments.services.wallet import (
    credit_wallet, debit_wallet, get_wallet,
    WalletError, InsufficientBalanceError,
)
from orders.models import Order, OrderItem
from products.models import Category, Product
from stores.models import Store

User = get_user_model()


class TestWalletReconciliation(TestCase):
    """Verify wallet balance consistency across operations."""

    databases = '__all__'

    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(
            category_name='Test', is_active=True
        )
        cls.user = User.objects.create_user(
            'wallet_tester',  # username (required by custom UserManager)
            email='wallet.test@test.io', password='Pass123!',
            full_name='Wallet Tester', is_verified=True, role='seller',
        )

    def setUp(self):
        # Reset wallet for each test
        wallet, _ = Wallet.objects.get_or_create(
            user=self.user, defaults={'balance': Decimal('0')}
        )
        wallet.balance = Decimal('0')
        wallet.save(update_fields=['balance'])

    def test_initial_balance_zero(self):
        """New wallet starts with zero balance."""
        wallet = get_wallet(self.user, lock=False)
        self.assertEqual(wallet.balance, Decimal('0'))

    def test_credit_increases_balance(self):
        """Credit should increase wallet balance by exact amount."""
        result = credit_wallet(
            self.user, Decimal('50000'), tx_type='topup',
            reference_type='test', reference_id='credit-001'
        )
        self.assertTrue(result['success'])
        self.assertEqual(result['balance_before'], Decimal('0'))
        self.assertEqual(result['balance_after'], Decimal('50000'))

        wallet = get_wallet(self.user, lock=False)
        self.assertEqual(wallet.balance, Decimal('50000'))

    def test_debit_decreases_balance(self):
        """Debit should decrease wallet balance by exact amount."""
        credit_wallet(
            self.user, Decimal('100000'), tx_type='topup',
            reference_type='test', reference_id='debit-prep'
        )

        result = debit_wallet(
            self.user, Decimal('30000'), tx_type='payment',
            reference_type='order', reference_id='order-001'
        )
        self.assertTrue(result['success'])
        self.assertEqual(result['balance_before'], Decimal('100000'))
        self.assertEqual(result['balance_after'], Decimal('70000'))

        wallet = get_wallet(self.user, lock=False)
        self.assertEqual(wallet.balance, Decimal('70000'))

    def test_insufficient_balance_raises_error(self):
        """Debiting more than balance should raise error."""
        with self.assertRaises(InsufficientBalanceError):
            debit_wallet(
                self.user, Decimal('50000'), tx_type='payment',
                reference_type='order', reference_id='insufficient-001'
            )

    def test_duplicate_transaction_prevention(self):
        """Same reference_type + reference_id should be detected as duplicate."""
        result1 = credit_wallet(
            self.user, Decimal('50000'), tx_type='topup',
            reference_type='midtrans', reference_id='trx-001'
        )
        self.assertTrue(result1['success'])
        self.assertFalse(result1.get('duplicate', False))

        # Same ref — should be blocked
        result2 = credit_wallet(
            self.user, Decimal('50000'), tx_type='topup',
            reference_type='midtrans', reference_id='trx-001'
        )
        self.assertTrue(result2['success'])
        self.assertTrue(result2.get('duplicate', False))

        # Balance should not have doubled
        wallet = get_wallet(self.user, lock=False)
        self.assertEqual(wallet.balance, Decimal('50000'))

    def test_negative_amount_rejected(self):
        """Credit/debit with zero or negative amount should raise error."""
        with self.assertRaises(WalletError):
            credit_wallet(
                self.user, Decimal('-10000'), tx_type='topup',
                reference_type='test', reference_id='neg-credit'
            )
        with self.assertRaises(WalletError):
            credit_wallet(
                self.user, Decimal('0'), tx_type='topup',
                reference_type='test', reference_id='zero-credit'
            )
        with self.assertRaises(WalletError):
            debit_wallet(
                self.user, Decimal('-10000'), tx_type='payment',
                reference_type='test', reference_id='neg-debit'
            )

    def test_multiple_transactions_consistency(self):
        """
        Perform multiple credits and debits, verify final balance
        matches cumulative sum of all transactions.
        """
        transactions = [
            ('credit', Decimal('100000'), 'topup', 'ref-1'),
            ('credit', Decimal('50000'), 'topup', 'ref-2'),
            ('debit', Decimal('30000'), 'payment', 'order-1'),
            ('debit', Decimal('15000'), 'payment', 'order-2'),
            ('credit', Decimal('25000'), 'refund', 'refund-1'),
            ('debit', Decimal('10000'), 'withdrawal', 'wd-1'),
        ]

        for tx_type, amount, tx_category, ref_id in transactions:
            if tx_type == 'credit':
                credit_wallet(
                    self.user, amount, tx_type=tx_category,
                    reference_type='test', reference_id=ref_id
                )
            else:
                debit_wallet(
                    self.user, amount, tx_type=tx_category,
                    reference_type='test', reference_id=ref_id
                )

        # Calculate expected balance
        expected = Decimal('0')
        for tx_type, amount, _, _ in transactions:
            if tx_type == 'credit':
                expected += amount
            else:
                expected -= amount

        wallet = get_wallet(self.user, lock=False)
        self.assertEqual(
            wallet.balance, expected,
            f'Expected balance Rp {expected}, got Rp {wallet.balance}'
        )

        # Verify transaction records match
        tx_sum = WalletTransaction.objects.filter(user=self.user).aggregate(
            net=Sum('amount')
        )['net'] or Decimal('0')
        self.assertEqual(wallet.balance, tx_sum)

    def test_transaction_audit_trail(self):
        """Every wallet operation should create a transaction record."""
        tx_count_before = WalletTransaction.objects.count()

        credit_wallet(
            self.user, Decimal('75000'), tx_type='topup',
            description='Top up test',
            reference_type='midtrans', reference_id='audit-001'
        )

        tx_count_after = WalletTransaction.objects.count()
        self.assertEqual(tx_count_after, tx_count_before + 1)

        tx = WalletTransaction.objects.filter(
            user=self.user
        ).first()
        self.assertEqual(tx.amount, Decimal('75000'))
        self.assertEqual(tx.tx_type, 'topup')
        self.assertEqual(tx.description, 'Top up test')
        self.assertEqual(tx.reference_type, 'midtrans')
        self.assertEqual(tx.reference_id, 'audit-001')
        self.assertEqual(tx.balance_before, Decimal('0'))
        self.assertEqual(tx.balance_after, Decimal('75000'))

    def test_concurrent_credit_no_double_spend(self):
        """
        Simulate two concurrent credits with same reference.
        Only one should be applied (idempotency).
        """
        result1 = credit_wallet(
            self.user, Decimal('100000'), tx_type='topup',
            reference_type='midtrans', reference_id='concurrent-001'
        )
        result2 = credit_wallet(
            self.user, Decimal('100000'), tx_type='topup',
            reference_type='midtrans', reference_id='concurrent-001'
        )

        self.assertTrue(result1['success'])
        self.assertFalse(result1.get('duplicate', False))
        self.assertTrue(result2['duplicate'])

        wallet = get_wallet(self.user, lock=False)
        self.assertEqual(wallet.balance, Decimal('100000'))


class TestAdminFeeReconciliation(TestCase):
    """Verify admin fee recording and consistency."""

    databases = '__all__'

    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(
            category_name='Test Fee', is_active=True
        )
        cls.seller_user = User.objects.create_user(
            'seller_fee',  # username (required)
            email='seller.fee@test.io', password='Pass123!',
            is_verified=True, role='seller',
        )
        cls.store = Store.objects.create(
            user=cls.seller_user, store_name='Toko Fee Test',
            status='active',
        )
        cls.product = Product.objects.create(
            store=cls.store, category=cls.category,
            product_name='Produk Fee', price=50000, stock=100,
            is_active=True,
        )

    def test_admin_fee_recorded_on_payment(self):
        """Admin fee (Rp 1.000) should be recorded when payment is marked as paid."""
        buyer = User.objects.create_user(
            'buyer_fee',  # username (required)
            email='buyer.fee@test.io', password='Pass123!',
            is_verified=True, role='buyer',
        )
        order = Order.objects.create(
            user=buyer, store=self.store,
            total_price=50000, delivery_address='Jl. Fee',
            recipient_name='Fee Buyer', recipient_phone='081',
            admin_fee=Decimal('1000'),
            admin_fee_buyer=Decimal('1500'),
            admin_fee_seller=Decimal('1000'),
        )

        payment = PaymentModel.objects.create(
            order=order, user=buyer, amount=50000,
            payment_type='bank_transfer',
        )
        payment.mark_as_paid()

        # Verify AdminFeeTransaction created
        fee_record = AdminFeeTransaction.objects.filter(order=order).first()
        self.assertIsNotNone(
            fee_record,
            'AdminFeeTransaction should be created after payment'
        )
        self.assertEqual(fee_record.amount, Decimal('1000'))
        self.assertEqual(fee_record.store, self.store)
        self.assertEqual(fee_record.payout_status, 'pending')

    def test_admin_fee_no_duplicate(self):
        """Marking payment as paid twice should not create duplicate admin fee."""
        buyer = User.objects.create_user(
            'buyer_fee2',  # username (required)
            email='buyer.fee2@test.io', password='Pass123!',
            is_verified=True, role='buyer',
        )
        order = Order.objects.create(
            user=buyer, store=self.store,
            total_price=50000, delivery_address='Jl. Fee 2',
            recipient_name='Fee2', recipient_phone='082',
            admin_fee=Decimal('1000'),
            admin_fee_buyer=Decimal('1500'),
            admin_fee_seller=Decimal('1000'),
        )

        payment = PaymentModel.objects.create(
            order=order, user=buyer, amount=50000,
            payment_type='bank_transfer',
        )
        payment.mark_as_paid()
        payment.mark_as_paid()  # second call

        fee_count = AdminFeeTransaction.objects.filter(order=order).count()
        self.assertEqual(fee_count, 1, 'Should only have one admin fee record')

    def test_order_calculate_totals_with_fees(self):
        """Verify order total calculation includes admin fees correctly.
        
        total_price = subtotal + shipping_cost - discount + admin_fee_buyer
        """
        buyer = User.objects.create_user(
            'buyer_totals',  # username (required)
            email='buyer.totals@test.io', password='Pass123!',
            is_verified=True, role='buyer',
        )
        order = Order.objects.create(
            user=buyer, store=self.store,
            total_price=0, delivery_address='Jl. Total',
            recipient_name='Total', recipient_phone='083',
            shipping_cost=Decimal('10000'),
            discount=Decimal('5000'),
            admin_fee=Decimal('1000'),
            admin_fee_buyer=Decimal('1500'),
            admin_fee_seller=Decimal('1000'),
        )
        
        # Create OrderItem so calculate_totals can compute subtotal
        OrderItem.objects.create(
            order=order, product=self.product,
            qty=5, price=Decimal('10000'),
        )
        order.refresh_from_db()
        order.calculate_totals()
        order.refresh_from_db()

        # subtotal = 5 * 10000 = 50000
        # total = 50000 + 10000 - 5000 + 1500 = 56500
        expected = Decimal('56500')
        self.assertEqual(order.total_price, expected)
