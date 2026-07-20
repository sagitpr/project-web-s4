"""
AI Habit & Gamification Engine.
Manages streaks, challenges, badges, XP, and behavioral loop optimization.
"""

import logging
from datetime import timedelta
from typing import Dict, List, Optional
from django.db.models import Count, Sum
from django.utils import timezone

logger = logging.getLogger(__name__)


class GamificationEngine:
    """
    Gamification engine powering habit formation and engagement loops.
    Uses behavioral psychology (habit loop: Cue → Routine → Reward).
    """

    XP_EVENTS = {
        'login': 10, 'order_completed': 50, 'review_written': 30,
        'store_follow': 5, 'ai_scan': 20, 'referral_made': 100,
        'wishlist_add': 5, 'cart_add': 3, 'product_view': 1,
        'chat_message': 2, 'search_query': 1, 'payment_success': 40,
    }

    def update_gamification(self, user, event_type: str = '') -> Dict:
        """Update gamification profile after a user action."""
        from ai_intelligence.models import GamificationProfile

        profile, _ = GamificationProfile.objects.get_or_create(user=user)

        # XP earned
        xp_gained = self.XP_EVENTS.get(event_type, 0)
        if xp_gained > 0:
            profile.xp_points += xp_gained
            profile.total_xp_earned += xp_gained
            profile.last_streak_activity = timezone.now()

            # Level up check
            while profile.xp_points >= profile.xp_to_next_level:
                profile.xp_points -= profile.xp_to_next_level
                profile.level += 1
                profile.xp_to_next_level = int(profile.xp_to_next_level * 1.5)
                profile.streak_multiplier = min(3.0, profile.streak_multiplier + 0.1)

        # Streak tracking
        self._update_streak(profile)

        # Habit loop phase
        profile.habit_loop_phase = self._determine_habit_phase(profile)

        profile.save()
        return {'xp_gained': xp_gained, 'level': profile.level, 'streak': profile.current_streak_days}

    def _update_streak(self, profile):
        """Update streak based on daily activity."""
        now = timezone.now()
        if not profile.last_streak_activity:
            return

        hours_since = (now - profile.last_streak_activity).total_seconds() / 3600

        if hours_since <= 36:  # Allow 12h grace
            pass  # Same day — no streak change needed
        elif hours_since <= 48:
            profile.current_streak_days += 1
        else:
            if profile.current_streak_days > profile.longest_streak_days:
                profile.longest_streak_days = profile.current_streak_days
            profile.current_streak_days = 0
            profile.streak_multiplier = 1.0

    def _determine_habit_phase(self, profile) -> str:
        """Determine current habit loop phase."""
        if profile.current_streak_days == 0:
            return 'discovery'
        elif profile.current_streak_days <= 3:
            return 'trigger'
        elif profile.current_streak_days <= 7:
            return 'action'
        elif profile.current_streak_days <= 21:
            return 'reward'
        elif profile.current_streak_days <= 66:
            return 'investment'
        return 'maintenance'

    def get_or_create_daily_challenges(self, user) -> List[Dict]:
        """Get or create daily challenges for a user."""
        from ai_intelligence.models import Challenge, UserChallengeProgress

        now = timezone.now()
        today = now.date()

        active = Challenge.objects.filter(
            is_active=True,
            challenge_type='daily',
            start_date__lte=now,
            end_date__gte=now,
        )

        results = []
        for challenge in active:
            progress, created = UserChallengeProgress.objects.get_or_create(
                user=user, challenge=challenge,
                defaults={'target_value': challenge.requirement_value}
            )
            results.append({
                'id': challenge.id,
                'name': challenge.name,
                'description': challenge.description,
                'progress': progress.current_value,
                'target': progress.target_value,
                'is_completed': progress.is_completed,
                'xp_reward': challenge.xp_reward,
                'badge_reward': challenge.badge_reward,
            })

        return results

    def update_challenge_progress(self, user, requirement_type: str, value: int = 1):
        """Update progress for challenges matching a requirement type."""
        from ai_intelligence.models import Challenge, UserChallengeProgress

        matching = Challenge.objects.filter(
            is_active=True,
            requirement_type=requirement_type,
            start_date__lte=timezone.now(),
            end_date__gte=timezone.now(),
        )

        for challenge in matching:
            progress, _ = UserChallengeProgress.objects.get_or_create(
                user=user, challenge=challenge,
                defaults={'target_value': challenge.requirement_value}
            )
            progress.current_value += value
            if progress.current_value >= progress.target_value and not progress.is_completed:
                progress.is_completed = True
                progress.completed_at = timezone.now()
                # Award XP directly from challenge
                from ai_intelligence.models import GamificationProfile
                profile, _ = GamificationProfile.objects.get_or_create(user=user)
                profile.xp_points += challenge.xp_reward
                profile.total_xp_earned += challenge.xp_reward
                while profile.xp_points >= profile.xp_to_next_level:
                    profile.xp_points -= profile.xp_to_next_level
                    profile.level += 1
                    profile.xp_to_next_level = int(profile.xp_to_next_level * 1.5)
                profile.save()
                if challenge.badge_reward:
                    badges = list(profile.badges_earned or [])
                    if challenge.badge_reward not in badges:
                        badges.append(challenge.badge_reward)
                        profile.badges_earned = badges
                        profile.total_badges = len(badges)
                        profile.save()
            progress.save()


# Singleton
_gamification_engine = None


def get_gamification_engine() -> GamificationEngine:
    global _gamification_engine
    if _gamification_engine is None:
        _gamification_engine = GamificationEngine()
    return _gamification_engine
