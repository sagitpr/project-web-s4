"""
AI Notification Generator for Engagement Engine.
Uses Gemini AI to create highly personalized Indonesian-language notifications
using psychological triggers: Curiosity Gap, Loss Aversion, FOMO,
Social Proof, Goal Gradient, Habit Loop, Variable Reward,
Positive Reinforcement, Personalization, Scarcity, Reciprocity, Progress Motivation.
"""

import json
import logging
from typing import Optional, Dict, Any, List
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.db.models import Sum, Avg, Count

from ai_services.gemini_client import get_gemini_client

logger = logging.getLogger(__name__)

# System prompt for the AI notification generator
SYSTEM_PROMPT = """Anda adalah AI Engagement & Retention Specialist untuk Warungio Marketplace Indonesia.
Tugas Anda adalah membuat notifikasi push yang sangat personal, engaging, dan tidak spam.

PRINSIP-PRINSIP PSIKOLOGIS YANG DIGUNAKAN:
1. Curiosity Gap: Buat penasaran, jangan beri semua informasi
2. Loss Aversion: Tekankan apa yang akan dilewatkan
3. FOMO: Fear of missing out — terbatas, waktu habis
4. Social Proof: "Sudah 1.234 pembeli lain membeli ini"
5. Goal Gradient: "Kurang 2 langkah lagi dapat reward!"
6. Habit Loop: Cue → Routine → Reward
7. Variable Reward: Kejutan reward yang tidak terduga
8. Positive Reinforcement: Apresiasi dan pengakuan
9. Personalization: Personalisasi maksimal dengan data pengguna
10. Scarcity: "Stok tersisa 3", "Hanya hari ini"
11. Reciprocity: Beri nilai dulu sebelum minta aksi
12. Progress Motivation: "90% menuju tujuan!"

PANDUAN:
- Selalu gunakan Bahasa Indonesia yang natural dan ramah
- Maksimal judul: 50 karakter
- Maksimal body: 120 karakter
- Jangan repetitif — variasi gaya setiap notifikasi
- Jangan terkesan spammy
- Gunakan data real user untuk personalisasi
- Sesuaikan tone dengan segmentasi user (buyer/seller)
- Cantumkan trigger psikologis yang digunakan

Keluarkan dalam format JSON dengan field: title, body, psychological_trigger, reasoning.
"""


class AINotificationGenerator:
    """
    AI-powered notification generator that creates personalized,
    psychologically-optimized notifications using Gemini AI.
    """

    def __init__(self):
        self.client = get_gemini_client()

    def generate(self, user, trigger_type: str, context: Dict = None) -> Optional[Dict[str, Any]]:
        """
        Generate a personalized notification for a user.
        
        Args:
            user: The target user
            trigger_type: Psychological or event trigger type
            context: Additional context data for personalization
            
        Returns:
            Dict with title, body, psychological_trigger, reasoning or None
        """
        from engagement.models import UserBehaviorProfile
        from accounts.models import User

        profile, _ = UserBehaviorProfile.objects.get_or_create(user=user)
        context = context or {}

        # Build rich user context
        user_context = self._build_user_context(user, profile, context)

        # Select appropriate prompt template
        prompt = self._build_prompt(trigger_type, user_context)

        # Call Gemini
        try:
            result = self.client.generate_structured(
                prompt=prompt,
                system_instruction=SYSTEM_PROMPT,
                temperature=0.7,
                max_output_tokens=512,
                cache_key=f'eng_notif_gen:{trigger_type}:{user.id}:{hash(str(context))}' if context else None,
            )

            if result and 'title' in result and 'body' in result:
                result['psychological_trigger'] = result.get('psychological_trigger', trigger_type)
                result['trigger_type'] = trigger_type
                result['ai_generated'] = True
                result['ai_model_version'] = 'gemini-2.0-flash'
                return result

            return None

        except Exception as e:
            logger.error("Gemini notification generation failed for user %s: %s", user.email, e)
            return self._fallback_notification(trigger_type, user_context)

    def generate_batch(self, users, trigger_type: str, context: Dict = None) -> List[Dict]:
        """
        Generate notifications for multiple users (for campaigns).
        
        Args:
            users: QuerySet or list of users
            trigger_type: Trigger type
            context: Shared context
            
        Returns:
            List of {user_id, title, body, trigger} dicts
        """
        results = []
        for user in users:
            notif = self.generate(user, trigger_type, context)
            if notif:
                notif['user_id'] = user.id
                results.append(notif)
        return results

    def _build_user_context(self, user, profile, context: Dict) -> Dict:
        """Build rich user context for AI personalization."""
        from orders.models import Order

        thirty_days_ago = timezone.now() - timedelta(days=30)

        recent_orders_count = Order.objects.filter(
            user=user, created_at__gte=thirty_days_ago
        ).count()

        last_order = Order.objects.filter(user=user).order_by('-created_at').first()
        last_order_amount = float(last_order.total_price) if last_order else 0

        return {
            'user_name': user.full_name or user.email.split('@')[0],
            'user_role': user.role,
            'city': profile.city or '',
            'engagement_score': profile.engagement_score,
            'retention_score': profile.retention_score,
            'loyalty_score': profile.loyalty_score,
            'inactivity_days': profile.inactivity_days,
            'total_orders': profile.total_orders,
            'recent_orders_count': recent_orders_count,
            'last_order_amount': last_order_amount,
            'favorite_categories': profile.favorite_categories[:3],
            'loyalty_tier': profile.loyalty_tier,
            'total_loyalty_points': profile.total_loyalty_points,
            'reward_progress_pct': profile.reward_progress_pct,
            'login_streak_days': profile.login_streak_days,
            'cart_abandon_rate': profile.cart_abandon_rate,
            'total_wishlist_items': profile.total_wishlist_adds - profile.total_wishlist_removes,
            'total_notifications_opened': profile.total_notifications_opened,
            'notification_open_rate': profile.notification_open_rate,
            'risk_level': profile.risk_level,
            # Merge external context
            **context,
        }

    def _build_prompt(self, trigger_type: str, user_context: Dict) -> str:
        """Build AI prompt based on trigger type and user context."""
        user_name = user_context.get('user_name', 'Pengguna')
        city = user_context.get('city', '')
        tier = user_context.get('loyalty_tier', 'bronze')
        points = user_context.get('total_loyalty_points', 0)
        progress = user_context.get('reward_progress_pct', 0)
        streak = user_context.get('login_streak_days', 0)
        inertia = user_context.get('inactivity_days', 0)
        engagement = user_context.get('engagement_score', 0)
        orders = user_context.get('total_orders', 0)
        recent_orders = user_context.get('recent_orders_count', 0)
        favorites = user_context.get('favorite_categories', [])
        cart_abandon = user_context.get('cart_abandon_rate', 0)
        wishlist_count = user_context.get('total_wishlist_items', 0)
        risk = user_context.get('risk_level', 'active')

        # Extra context from caller
        extra = {k: v for k, v in user_context.items() if k not in [
            'user_name', 'user_role', 'city', 'engagement_score', 'retention_score',
            'loyalty_score', 'inactivity_days', 'total_orders', 'recent_orders_count',
            'last_order_amount', 'favorite_categories', 'loyalty_tier',
            'total_loyalty_points', 'reward_progress_pct', 'login_streak_days',
            'cart_abandon_rate', 'total_wishlist_items', 'total_notifications_opened',
            'notification_open_rate', 'risk_level'
        ]}

        extra_context = json.dumps(extra, indent=2) if extra else 'Tidak ada konteks tambahan'

        prompt = f"""
Buat SATU notifikasi push dalam Bahasa Indonesia yang natural dan engaging untuk pengguna Warungio.

DATA PENGGUNA:
- Nama: {user_name}
- Kota: {city or 'Tidak diketahui'}
- Role: {user_context.get('user_role', 'buyer')}
- Total Pesanan: {orders}
- Pesanan 30 Hari Terakhir: {recent_orders}
- Skor Engagement: {engagement:.1f}/100
- Skor Loyalitas: {user_context.get('loyalty_score', 0):.1f}/100
- Tier Loyalty: {tier}
- Poin Loyalty: {points}
- Progress Reward: {progress:.0f}%
- Hari Tidak Aktif: {inertia}
- Streak Login: {streak} hari
- Kategori Favorit: {', '.join(favorites) if favorites else 'Belum ada'}
- Jumlah Wishlist: {wishlist_count}
- Cart Abandon Rate: {cart_abandon:.0%}
- Tingkat Risiko: {risk}
- Open Rate Notifikasi: {user_context.get('notification_open_rate', 0):.0%}

TRIGGER PSIKOLOGIS YANG DIGUNAKAN: {trigger_type}

KONTEKS TAMBAHAN DARI PEMANGGIL:
{extra_context}

INSTRUKSI:
1. Buat judul (max 50 karakter) yang menggunakan trigger "{trigger_type}"
2. Buat body (max 120 karakter) yang personal dan engaging
3. Tentukan psychological_trigger yang tepat dari: curiosity_gap, loss_aversion, fomo, social_proof, goal_gradient, habit_loop, variable_reward, positive_reinforcement, personalization, scarcity, reciprocity, progress_motivation
4. Berikan reasoning singkat kenapa notifikasi ini relevan

Keluarkan JSON:
{{
  "title": "...",
  "body": "...",
  "psychological_trigger": "...",
  "reasoning": "..."
}}
"""
        return prompt

    def _fallback_notification(self, trigger_type: str, user_context: Dict) -> Dict:
        """Fallback notification when AI generation fails."""
        user_name = user_context.get('user_name', 'Pengguna')

        fallbacks = {
            'personalization': {
                'title': f'Hai {user_name}, ada yang baru nih! 🔥',
                'body': 'Produk dan promo terbaru sudah menunggu. Cek sekarang!',
                'psychological_trigger': 'personalization',
                'reasoning': 'Fallback: AI unavailable, using personalized name',
            },
            'fomo': {
                'title': 'Jangan sampai ketinggalan! ⏰',
                'body': 'Promo spesial hari ini akan segera berakhir!',
                'psychological_trigger': 'fomo',
                'reasoning': 'Fallback: AI unavailable',
            },
            'scarcity': {
                'title': 'Stok terbatas! 🏃',
                'body': 'Beberapa produk favoritmu tinggal sedikit lagi!',
                'psychological_trigger': 'scarcity',
                'reasoning': 'Fallback: AI unavailable',
            },
            'inactivity': {
                'title': f'Kami kangen kamu, {user_name}! 💚',
                'body': 'Sudah lama tidak belanja. Yuk lihat produk terbaru!',
                'psychological_trigger': 'personalization',
                'reasoning': 'Fallback: AI unavailable, re-engagement',
            },
            'goal_gradient': {
                'title': f'{user_name}, kamu hampir sampai! 🎯',
                'body': f'Progress kamu sudah {user_context.get("reward_progress_pct", 0):.0f}%. Ayo selesaikan!',
                'psychological_trigger': 'goal_gradient',
                'reasoning': 'Fallback: AI unavailable',
            },
            'loss_aversion': {
                'title': 'Poin kamu akan hangus! ⚠️',
                'body': f'{user_context.get("total_loyalty_points", 0)} poin akan kedaluwarsa. Tukarkan sekarang!',
                'psychological_trigger': 'loss_aversion',
                'reasoning': 'Fallback: AI unavailable',
            },
            'social_proof': {
                'title': 'Yang lain sudah pada belanja! 👥',
                'body': f'Ribuan pembeli puas dengan produk di {user_context.get("favorite_categories", ["Warungio"])[0] if user_context.get("favorite_categories") else "Warungio"}.',
                'psychological_trigger': 'social_proof',
                'reasoning': 'Fallback: AI unavailable',
            },
        }

        # Try to match the trigger
        if trigger_type in fallbacks:
            return fallbacks[trigger_type]

        # Default fallback
        return {
            'title': f'Halo {user_name}! Ada yang baru di Warungio 🎉',
            'body': 'Yuk lihat produk dan promo terbaru yang mungkin kamu suka!',
            'psychological_trigger': 'personalization',
            'reasoning': 'Fallback: AI unavailable, generic greeting',
        }

    # ═══════════════════════════════════════════════════════════════
    # SPECIALIZED GENERATORS
    # ═══════════════════════════════════════════════════════════════

    def generate_abandoned_cart(self, user, cart_items: list, total_value: float) -> Optional[Dict]:
        """Generate abandoned cart reminder using Loss Aversion + FOMO."""
        context = {
            'cart_items': [{'name': item.get('product_name', 'Produk'), 'qty': item.get('qty', 1)} for item in cart_items],
            'total_value': total_value,
            'item_count': len(cart_items),
        }
        return self.generate(user, 'loss_aversion', context)

    def generate_inactivity_reminder(self, user, days_inactive: int) -> Optional[Dict]:
        """Generate re-engagement notification for inactive users."""
        context = {'days_inactive': days_inactive}
        return self.generate(user, 'fomo', context)

    def generate_wishlist_promo(self, user, wishlist_items: list) -> Optional[Dict]:
        """Generate notification about wishlist items on promo."""
        context = {
            'wishlist_item_count': len(wishlist_items),
            'wishlist_items': [item.get('product_name', '') for item in wishlist_items[:3]],
        }
        return self.generate(user, 'scarcity', context)

    def generate_loyalty_milestone(self, user, progress: float, next_reward: str) -> Optional[Dict]:
        """Generate progress motivation notification."""
        context = {
            'progress_pct': progress,
            'next_reward': next_reward,
        }
        return self.generate(user, 'goal_gradient', context)

    def generate_birthday_notification(self, user, reward_info: Dict) -> Optional[Dict]:
        """Generate birthday notification with rewards."""
        context = {
            'reward_info': reward_info,
            'is_birthday': True,
        }
        return self.generate(user, 'reciprocity', context)

    def generate_flash_sale(self, user, products: list, time_left: str) -> Optional[Dict]:
        """Generate flash sale notification using scarcity + FOMO."""
        context = {
            'flash_products': [p.get('name', '') for p in products[:3]],
            'time_left': time_left,
            'is_flash_sale': True,
        }
        return self.generate(user, 'scarcity', context)

    def generate_restock_alert(self, user, product_name: str, store_name: str) -> Optional[Dict]:
        """Generate restock notification for favorited product."""
        context = {
            'product_name': product_name,
            'store_name': store_name,
            'is_restock': True,
        }
        return self.generate(user, 'fomo', context)

    def generate_ai_recommendation(self, user, recommended_products: list, reason: str) -> Optional[Dict]:
        """Generate AI-powered recommendation notification."""
        context = {
            'recommended_products': [p.get('name', '') for p in recommended_products[:3]],
            'recommendation_reason': reason,
        }
        return self.generate(user, 'personalization', context)

    def generate_referral_request(self, user, reward_amount: int) -> Optional[Dict]:
        """Generate referral program notification using reciprocity."""
        context = {
            'reward_amount': reward_amount,
            'is_referral': True,
        }
        return self.generate(user, 'reciprocity', context)

    def generate_streak_milestone(self, user, streak_days: int) -> Optional[Dict]:
        """Generate streak milestone celebration."""
        context = {
            'streak_days': streak_days,
            'is_streak': True,
        }
        return self.generate(user, 'positive_reinforcement', context)

    def generate_order_update(self, user, order_number: str, status: str, eta: str = None) -> Optional[Dict]:
        """Generate order update notification."""
        context = {
            'order_number': order_number,
            'order_status': status,
            'eta': eta or '',
        }
        return self.generate(user, 'habit_loop', context)

    def generate_review_request(self, user, product_name: str, days_since_delivery: int) -> Optional[Dict]:
        """Generate review request with reciprocity trigger."""
        context = {
            'product_name': product_name,
            'days_since_delivery': days_since_delivery,
        }
        return self.generate(user, 'reciprocity', context)

    def generate_seller_performance(self, user, stats: Dict) -> Optional[Dict]:
        """Generate seller performance notification."""
        context = {
            'seller_stats': stats,
            'is_seller': True,
        }
        return self.generate(user, 'positive_reinforcement', context)

    def generate_security_alert(self, user, alert_type: str) -> Optional[Dict]:
        """Generate security alert notification."""
        context = {
            'alert_type': alert_type,
            'is_security': True,
        }
        return self.generate(user, 'loss_aversion', context)


# Singleton
_generator = None


def get_ai_notification_generator() -> AINotificationGenerator:
    global _generator
    if _generator is None:
        _generator = AINotificationGenerator()
    return _generator
