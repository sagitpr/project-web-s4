"""
AI Notification Generator.
Creates personalized promotional messages, reminders, and recommendations
for buyers based on purchase history and preferences using Gemini API.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import timedelta
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.core.cache import cache

from accounts.models import User
from orders.models import Order, OrderItem
from products.models import Product, Favorite
from stores.models import Store
from .gemini_client import get_gemini_client

logger = logging.getLogger('django_backend.ai_services.notification')


class AINotificationGenerator:
    """
    AI-powered notification and promotion message generator.
    Creates personalized messages based on user behavior and preferences.
    """

    def __init__(self):
        self.client = get_gemini_client()

    def generate_personalized_promo(self, user, store=None) -> Optional[Dict[str, Any]]:
        """Generate personalized promotion message for a buyer."""
        # Get user's purchase history
        recent_orders = Order.objects.filter(
            user=user,
            created_at__gte=timezone.now() - timedelta(days=60),
        ).order_by('-created_at')[:5]

        # Get favorite categories
        favorite_cats = Favorite.objects.filter(
            user=user,
        ).values_list('product__category__category_name', flat=True).distinct()[:3]

        # Get frequently bought products
        bought_products = OrderItem.objects.filter(
            order__user=user,
        ).values('product_name').annotate(
            total=Sum('qty')
        ).order_by('-total')[:5]

        context = {
            'user_name': user.full_name or user.email.split('@')[0],
            'recent_orders': len(recent_orders),
            'favorite_categories': list(favorite_cats),
            'frequent_products': [p['product_name'] for p in bought_products],
        }

        prompt = (
            f"Anda adalah AI marketing untuk Warungio Marketplace.\n\n"
            f"Data Pengguna:\n"
            f"Nama: {context['user_name']}\n"
            f"Pesanan Terakhir: {context['recent_orders']} dalam 60 hari\n"
            f"Kategori Favorit: {', '.join(context['favorite_categories']) or 'Belum ada'}\n"
            f"Produk Sering Dibeli: {', '.join(context['frequent_products']) or 'Belum ada'}\n\n"
            f"{'Promo Toko: ' + store.store_name if store else ''}\n\n"
            "Buat pesan promosi personal untuk pengguna ini.\n\n"
            "Kembalikan JSON:\n"
            "{\n"
            '  "title": "Judul notifikasi pendek menarik (maks 50 chars)",\n'
            '  "body": "Isi pesan personal dalam Bahasa Indonesia (maks 150 chars)",\n'
            '  "message_type": "promo|reminder|recommendation|restock",\n'
            '  "call_to_action": "Aksi yang diharapkan",\n'
            '  "target_url": "/produk/rekomendasi/",\n'
            '  "priority": "high|normal|low",\n'
            '  "reasoning": "Kenapa pesan ini relevan untuk user ini"\n'
            "}"
        )

        result = self.client.generate_structured(
            prompt=prompt,
            temperature=0.7,
            cache_key=f'ai_notif_promo:{user.id}:{store.id if store else "all"}',
        )

        return result

    def generate_restock_alert(self, user, product) -> Optional[Dict[str, Any]]:
        """Generate restock notification for a previously out-of-stock product."""
        prompt = (
            f"Anda adalah AI notifikasi untuk Warungio.\n\n"
            f"Produk {product.product_name} sudah tersedia lagi!\n"
            f"Harga: Rp {product.price:,.0f}\n"
            f"Toko: {product.store.store_name if product.store else 'Warungio'}\n"
            f"Stok: {product.stock}\n\n"
            "Buat notifikasi yang memberitahu pengguna bahwa produk favorit mereka sudah tersedia.\n\n"
            "Kembalikan JSON:\n"
            "{\n"
            '  "title": "Judul notifikasi",\n'
            '  "body": "Pesan dalam Bahasa Indonesia",\n'
            '  "priority": "high"\n'
            "}"
        )

        return self.client.generate_structured(prompt=prompt, temperature=0.5)

    def generate_abandoned_cart_reminder(self, user, cart_items: list) -> Optional[Dict[str, Any]]:
        """Generate reminder for abandoned cart."""
        items_text = "\n".join([
            f"- {item.get('product_name', 'Produk')} x{item.get('qty', 1)} = Rp {item.get('subtotal', 0):,.0f}"
            for item in cart_items
        ])

        prompt = (
            f"Anda adalah AI notifikasi Warungio.\n\n"
            f"Pengguna {user.full_name or user.email} memiliki item di keranjang yang belum dibayar:\n"
            f"{items_text}\n\n"
            "Buat pesan pengingat ramah untuk mendorong penyelesaian pesanan.\n\n"
            "Kembalikan JSON:\n"
            "{\n"
            '  "title": "Judul pengingat",\n'
            '  "body": "Pesan ramah dalam Bahasa Indonesia",\n'
            '  "priority": "normal"\n'
            "}"
        )

        return self.client.generate_structured(prompt=prompt, temperature=0.7)

    def generate_birthday_promo(self, user) -> Optional[Dict[str, Any]]:
        """Generate birthday promo message."""
        prompt = (
            f"Anda adalah AI marketing Warungio.\n\n"
            f"Pengguna: {user.full_name or user.email}\n\n"
            "Buat pesan ulang tahun personal dengan promo spesial.\n\n"
            "Kembalikan JSON:\n"
            "{\n"
            '  "title": "Selamat Ulang Tahun! 🎂",\n'
            '  "body": "Pesan ulang tahun dengan promo dalam Bahasa Indonesia",\n'
            '  "voucher_code": "BDAY" + angka acak 4 digit,\n'
            '  "discount_percent": 10,\n'
            '  "priority": "high"\n'
            "}"
        )

        return self.client.generate_structured(prompt=prompt, temperature=0.7)

    def generate_marketing_campaign(self, store, campaign_type: str = 'promo') -> Optional[Dict[str, Any]]:
        """Generate marketing campaign message for a store."""
        prompt = (
            f"Anda adalah AI marketing untuk toko {store.store_name} di Warungio.\n\n"
            f"Buat pesan kampanye {campaign_type} yang menarik untuk pelanggan.\n\n"
            "Kembalikan JSON:\n"
            "{\n"
            '  "headline": "Judul kampanye",\n'
            '  "description": "Deskripsi kampanye",\n'
            '  "call_to_action": "CTA text",\n'
            '  "target_audience": "Target pelanggan"\n'
            "}"
        )

        return self.client.generate_structured(prompt=prompt, temperature=0.7)


def get_notification_generator() -> AINotificationGenerator:
    return AINotificationGenerator()
