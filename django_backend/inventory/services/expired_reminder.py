"""
AI Expired Reminder Service — Warungio Marketplace.

Monitors product batches approaching expiry and generates:
- Expiry notifications (7 days, 3 days, 1 day, expired)
- Discount recommendations (percentage based on days remaining)
- Bundling suggestions (pair with other products)
- Flash sale suggestions for urgent items
- Auto-status updates (fresh → expiring_soon → expired)
"""

import logging
from datetime import date, timedelta, datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional
from django.db import transaction
from django.db.models import Q, Sum, F
from django.utils import timezone

from ..models import ProductBatch, ExpiryNotification, StockAlert, MasterProduct
from inventory.services.fefo_engine import get_expiry_summary

logger = logging.getLogger('django_backend.inventory.expired_reminder')


# ── Discount Tiers based on days remaining ──
DISCOUNT_TIERS = [
    {'days_min': 0, 'days_max': 3, 'discount_pct': 60, 'type': 'flash_sale',
     'label': 'Diskon Besar!', 'urgency': 'critical'},
    {'days_min': 4, 'days_max': 7, 'discount_pct': 40, 'type': 'discount',
     'label': 'Diskon Spesial', 'urgency': 'high'},
    {'days_min': 8, 'days_max': 14, 'discount_pct': 25, 'type': 'discount',
     'label': 'Diskon Sedang', 'urgency': 'medium'},
    {'days_min': 15, 'days_max': 30, 'discount_pct': 15, 'type': 'promo',
     'label': 'Promo Ringan', 'urgency': 'low'},
]


class AIExpiredReminder:
    """
    AI-powered expiry monitoring and discount recommendation engine.
    
    Features:
    - Check all batches approaching expiry
    - Generate tiered discount recommendations
    - Suggest bundling with complementary products
    - Identify flash sale candidates
    - Send expiry notifications (deduplicated)
    - Auto-update batch status
    """

    def __init__(self):
        pass

    # ── Check All Stores ──

    def run_global_expiry_check(self) -> Dict[str, Any]:
        """
        Run expiry check for ALL stores.
        Called by Celery Beat scheduler.
        
        Returns summary of notifications sent and batches affected.
        """
        stores = set()
        for batch in ProductBatch.objects.filter(
            is_active=True,
            current_quantity__gt=0,
        ).values_list('store_id', flat=True).distinct():
            stores.add(batch)

        total_alerts = 0
        total_batches = 0
        store_results = []

        for store_id in stores:
            result = self.check_store_expiry(store_id)
            if result:
                store_results.append(result)
                total_alerts += result.get('notifications_sent', 0)
                total_batches += result.get('batches_checked', 0)

        return {
            'stores_checked': len(stores),
            'total_batches_checked': total_batches,
            'total_notifications_sent': total_alerts,
            'store_results': store_results,
            'checked_at': timezone.now().isoformat(),
        }

    # ── Check Single Store ──

    def check_store_expiry(self, store_id: int) -> Dict[str, Any]:
        """
        Check all batches in a store for expiry status.
        
        Returns:
            dict with batches affected, notifications sent, discount recommendations
        """
        today = timezone.now().date()
        batches = ProductBatch.objects.filter(
            store_id=store_id,
            is_active=True,
            current_quantity__gt=0,
        ).select_related('master_product', 'store').order_by('expiry_date')

        notifications_sent = 0
        expiring_batches = []
        expired_batches = []
        discount_recommendations = []

        for batch in batches:
            days_remaining = (batch.expiry_date - today).days
            old_status = batch.status
            new_status = batch._calculate_status(today)

            # Update status if changed
            if new_status != old_status:
                batch.status = new_status
                batch.save(update_fields=['status', 'updated_at', 'shelf_life_remaining_pct'])

            # Skip if already disposed or fresh with plenty of time
            if new_status == 'disposed':
                continue
            if new_status == 'fresh' and days_remaining > 30:
                continue

            product_name = batch.master_product.product_name if batch.master_product else 'Unknown'
            batch_info = {
                'batch_id': batch.id,
                'product_name': product_name,
                'barcode': batch.master_product.barcode if batch.master_product else '',
                'current_quantity': float(batch.current_quantity),
                'unit': batch.unit,
                'expiry_date': batch.expiry_date.isoformat(),
                'days_remaining': days_remaining,
                'status': new_status,
                'shelf_life_pct': float(batch.shelf_life_remaining_pct),
                'purchase_price': float(batch.purchase_price) if batch.purchase_price else None,
                'category': batch.master_product.category if batch.master_product else '',
            }

            if new_status == 'expired':
                expired_batches.append(batch_info)
            elif days_remaining <= 30:
                expiring_batches.append(batch_info)
                # Generate discount recommendation
                discount = self.recommend_discount(days_remaining, batch)
                if discount:
                    discount_recommendations.append(discount)

            # Send notification if not already sent
            if days_remaining <= 7 or new_status == 'expired':
                notif_type = 'expired' if new_status == 'expired' else 'expiring_soon'
                sent = self._send_notification(batch, notif_type, days_remaining)
                if sent:
                    notifications_sent += 1

        # Generate bundling suggestions for expiring items
        bundling_suggestions = self.suggest_bundling(expiring_batches)

        return {
            'store_id': store_id,
            'batches_checked': batches.count(),
            'expiring_batches': len(expiring_batches),
            'expired_batches': len(expired_batches),
            'notifications_sent': notifications_sent,
            'discount_recommendations': discount_recommendations,
            'bundling_suggestions': bundling_suggestions,
            'flash_sale_candidates': [
                b for b in expiring_batches if b['days_remaining'] <= 3
            ],
            'checked_at': timezone.now().isoformat(),
        }

    # ── Discount Recommendation ──

    def recommend_discount(
        self,
        days_remaining: int,
        batch: ProductBatch,
    ) -> Optional[Dict[str, Any]]:
        """
        Recommend discount based on days remaining until expiry.
        
        Uses DISCOUNT_TIERS to determine appropriate discount percentage.
        """
        for tier in DISCOUNT_TIERS:
            if tier['days_min'] <= days_remaining <= tier['days_max']:
                purchase_price = float(batch.purchase_price) if batch.purchase_price else None
                purchase_price_float = purchase_price or 0.0
                estimated_original_price = purchase_price_float * 1.3 if purchase_price_float > 0 else None
                discounted_price = None
                if estimated_original_price:
                    discounted_price = round(
                        estimated_original_price * (1 - tier['discount_pct'] / 100), 2
                    )

                return {
                    'batch_id': batch.id,
                    'product_name': batch.master_product.product_name if batch.master_product else 'Unknown',
                    'days_remaining': days_remaining,
                    'recommended_discount_pct': tier['discount_pct'],
                    'discount_type': tier['type'],
                    'label': tier['label'],
                    'urgency': tier['urgency'],
                    'current_quantity': float(batch.current_quantity),
                    'unit': batch.unit,
                    'estimated_original_price': estimated_original_price,
                    'suggested_price': discounted_price,
                    'suggestion': self._get_discount_message(
                        batch, days_remaining, tier['discount_pct'], tier['type']
                    ),
                }

        return None

    def _get_discount_message(
        self, batch: ProductBatch, days: int, discount_pct: int, discount_type: str
    ) -> str:
        """Generate Indonesian discount recommendation message."""
        name = batch.master_product.product_name if batch.master_product else 'Produk'
        qty = float(batch.current_quantity)

        if discount_type == 'flash_sale':
            return (
                f"⚠️ **URGEN!** {name} ({qty:.0f} {batch.unit}) akan kedaluwarsa "
                f"dalam {days} hari. **Rekomendasi: Flash Sale diskon {discount_pct}%** "
                "sekarang juga! Buat banner 'Hari Terakhir' di etalase."
            )
        elif discount_type == 'discount':
            return (
                f"📢 {name} ({qty:.0f} {batch.unit}) tersisa {days} hari. "
                f"**Rekomendasi: Beri diskon {discount_pct}%** dan pasang label "
                "'Segera Habis' untuk menarik pembeli."
            )
        elif discount_type == 'promo':
            return (
                f"💡 {name} ({qty:.0f} {batch.unit}) akan kedaluwarsa {days} hari lagi. "
                f"**Rekomendasi: Diskon ringan {discount_pct}%** atau bundle dengan produk lain."
            )
        return (
            f"{name}: {qty:.0f} {batch.unit} tersisa, {days} hari sebelum EXP. "
            f"Pertimbangkan diskon {discount_pct}%."
        )

    # ── Bundling Suggestions ──

    def suggest_bundling(
        self,
        expiring_batches: List[Dict[str, Any]],
        max_suggestions: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Suggest product bundling with complementary items.
        
        Pairs expiring products with fast-moving complementary products
        to encourage bundled purchases.
        """
        if len(expiring_batches) < 2:
            return []

        suggestions = []
        category_groups = {}

        # Group by category
        for batch in expiring_batches:
            cat = batch.get('category', 'Umum')
            if cat not in category_groups:
                category_groups[cat] = []
            category_groups[cat].append(batch)

        # Generate bundles within same category
        for cat, batches in category_groups.items():
            if len(batches) < 2:
                continue

            # Sort by urgency
            batches.sort(key=lambda b: b['days_remaining'])

            # Pair most urgent with another in same category
            for i in range(min(len(batches) - 1, max_suggestions)):
                bundle = {
                    'bundle_name': f"Paket Hemat {cat}",
                    'products': [
                        {
                            'name': batches[i]['product_name'],
                            'qty': batches[i]['current_quantity'],
                            'days_remaining': batches[i]['days_remaining'],
                            'suggested_discount': DISCOUNT_TIERS[0]['discount_pct']
                                if batches[i]['days_remaining'] <= 3
                                else DISCOUNT_TIERS[1]['discount_pct'],
                        },
                        {
                            'name': batches[i + 1]['product_name'],
                            'qty': batches[i + 1]['current_quantity'],
                            'days_remaining': batches[i + 1]['days_remaining'],
                            'suggested_discount': DISCOUNT_TIERS[2]['discount_pct'],
                        },
                    ],
                    'suggested_bundle_discount': 10,  # Extra 10% off bundle
                    'suggestion': (
                        f"Bundel '{batches[i]['product_name']}' dengan "
                        f"'{batches[i + 1]['product_name']}' dengan diskon "
                        f"tambahan 10% untuk mendorong penjualan cepat!"
                    ),
                }
                suggestions.append(bundle)

        return suggestions[:max_suggestions]

    # ── Flash Sale Suggestions ──

    def get_flash_sale_candidates(
        self,
        store_id: int,
        min_quantity: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Get products that need urgent flash sale (<=3 days to expiry).
        
        Returns prioritized list of flash sale candidates.
        """
        today = timezone.now().date()
        threshold = today + timedelta(days=3)

        batches = ProductBatch.objects.filter(
            store_id=store_id,
            is_active=True,
            current_quantity__gte=min_quantity,
            expiry_date__lte=threshold,
            expiry_date__gte=today,
        ).select_related('master_product').order_by('expiry_date')

        candidates = []
        for batch in batches:
            days = (batch.expiry_date - today).days
            purchase_price_float = float(batch.purchase_price) if batch.purchase_price else 0.0
            discounted_price = round(purchase_price_float * 0.4, 2) if purchase_price_float > 0 else None  # 60% off

            candidates.append({
                'batch_id': batch.id,
                'product_name': batch.master_product.product_name,
                'barcode': batch.master_product.barcode,
                'quantity': float(batch.current_quantity),
                'unit': batch.unit,
                'days_remaining': days,
                'original_price': purchase_price_float,
                'flash_sale_price': discounted_price,
                'discount_pct': 60,
                'urgency': 'critical' if days <= 1 else 'high',
                'suggestion': (
                    f"🚨 FLASH SALE! {batch.master_product.product_name} "
                    f"({float(batch.current_quantity):.0f} {batch.unit}) — "
                    f"Diskon 60%! "
                    f"sebelum kedaluwarsa {days} hari lagi!"
                ),
            })

        return candidates

    # ── Discount Recommendation for Seller Dashboard ──

    def get_seller_discount_recommendations(
        self,
        store_id: int,
    ) -> Dict[str, Any]:
        """
        Get comprehensive discount recommendations for seller dashboard widget.
        
        Returns:
            dict with:
            - total_expiring: count
            - flash_sale_count: urgent items
            - recommendations: list of discount suggestions
            - bundling: list of bundling suggestions
            - estimated_revenue_recovery: potential revenue from discount sales
        """
        result = self.check_store_expiry(store_id)

        recommendations = []
        for disc in result.get('discount_recommendations', []):
            recommendations.append({
                'product_name': disc['product_name'],
                'discount_pct': disc['recommended_discount_pct'],
                'type': disc['discount_type'],
                'urgency': disc['urgency'],
                'current_stock': disc['current_quantity'],
                'unit': disc['unit'],
                'suggested_price': disc['suggested_price'],
                'message': disc['suggestion'],
            })

        # Calculate estimated recovery
        total_stock_value = sum(
            (r.get('estimated_original_price') or 0) * (r.get('current_quantity') or 0)
            for r in result.get('discount_recommendations', [])
        )
        potential_recovery = sum(
            (r.get('suggested_price', 0) or 0) * (r.get('current_quantity') or 0)
            for r in result.get('discount_recommendations', []) if r.get('suggested_price')
        )
        loss_without_action = total_stock_value - potential_recovery

        return {
            'store_id': store_id,
            'total_expiring': result.get('expiring_batches', 0),
            'total_expired': result.get('expired_batches', 0),
            'flash_sale_count': len(result.get('flash_sale_candidates', [])),
            'recommendations': recommendations,
            'bundling_suggestions': result.get('bundling_suggestions', []),
            'flash_sale_candidates': [
                {
                    'product_name': c['product_name'],
                    'quantity': c.get('quantity') or c.get('current_quantity') or 0,
                    'days_remaining': c.get('days_remaining', 0),
                    'discount_pct': c.get('discount_pct', 60),
                    'flash_sale_price': c.get('flash_sale_price'),
                }
                for c in result.get('flash_sale_candidates', [])
            ],
            'financial_impact': {
                'total_stock_value_at_risk': round(total_stock_value, 2),
                'potential_recovery_with_discount': round(potential_recovery, 2),
                'estimated_loss_without_action': round(loss_without_action, 2),
                'recovery_rate_pct': round(
                    (potential_recovery / total_stock_value * 100)
                    if total_stock_value > 0 else 0, 1
                ),
            },
            'generated_at': timezone.now().isoformat(),
        }

    # ── Send Expiry Notification (deduplicated) ──

    def _send_notification(
        self,
        batch: ProductBatch,
        notification_type: str,
        days_remaining: int,
    ) -> bool:
        """Send expiry notification if not already sent (deduplication)."""
        try:
            # Check if notification already sent
            existing = ExpiryNotification.objects.filter(
                batch=batch,
                notification_type=notification_type,
            ).exists()

            if existing:
                return False

            notif_kwargs = {
                'batch': batch,
                'store': batch.store,
                'notification_type': notification_type,
            }
            # Only pass days_remaining if the field exists on the model
            from inventory.models import ExpiryNotification as EN
            if hasattr(EN, 'days_remaining'):
                notif_kwargs['days_remaining'] = days_remaining
            ExpiryNotification.objects.create(**notif_kwargs)

            logger.info(
                f"Expiry notification sent: {batch.master_product.product_name} "
                f"({notification_type}, {days_remaining} days remaining)"
            )
            return True

        except Exception as e:
            logger.warning(f"Failed to send expiry notification: {e}")
            return False

    # ── Get Dashboard Widget Data ──

    def get_dashboard_widget_data(self, store_id: int) -> Dict[str, Any]:
        """Get data for seller dashboard Expired Reminder widget."""
        today = timezone.now().date()

        # Count batches by status
        stats = ProductBatch.objects.filter(
            store_id=store_id, is_active=True, current_quantity__gt=0
        ).aggregate(
            total=Sum('current_quantity'),
            fresh_count=Sum('current_quantity', filter=Q(status='fresh')),
            expiring_soon_count=Sum('current_quantity', filter=Q(status='expiring_soon')),
            expired_count=Sum('current_quantity', filter=Q(status='expired')),
        )

        # Get nearest expiring products (top 5)
        nearest_expiry = ProductBatch.objects.filter(
            store_id=store_id,
            is_active=True,
            current_quantity__gt=0,
            status__in=['fresh', 'expiring_soon'],
        ).select_related('master_product').order_by('expiry_date')[:5]

        expiring_list = []
        for batch in nearest_expiry:
            days = (batch.expiry_date - today).days
            discount = None
            for tier in DISCOUNT_TIERS:
                if tier['days_min'] <= days <= tier['days_max']:
                    discount = tier
                    break

            expiring_list.append({
                'batch_id': batch.id,
                'product_name': batch.master_product.product_name,
                'current_stock': float(batch.current_quantity),
                'unit': batch.unit,
                'expiry_date': batch.expiry_date.isoformat(),
                'days_remaining': days,
                'status': batch.status,
                'recommended_discount_pct': discount['discount_pct'] if discount else None,
                'discount_label': discount['label'] if discount else '',
            })

        return {
            'store_id': store_id,
            'total_stock': float(stats.get('total', 0) or 0),
            'fresh_stock': float(stats.get('fresh_count', 0) or 0),
            'expiring_soon_stock': float(stats.get('expiring_soon_count', 0) or 0),
            'expired_stock': float(stats.get('expired_count', 0) or 0),
            'expiring_count': len(expiring_list),
            'nearest_expiring': expiring_list,
            'checked_at': timezone.now().isoformat(),
        }


# ── Singleton ──
_reminder = None


def get_expired_reminder() -> AIExpiredReminder:
    global _reminder
    if _reminder is None:
        _reminder = AIExpiredReminder()
    return _reminder
