"""
AI Timing Engine for Engagement Engine.
Determines the optimal time to deliver each notification based on:
- User's historical active hours (preferred_hour_start/end)
- Peak activity hours
- Notification open rate by hour
- User timezone
- Notification priority and urgency
- Quiet hours configuration
- Weekend vs weekday patterns
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)


class TimingEngine:
    """
    AI-powered timing engine that determines the optimal delivery time
    for each notification based on user behavior patterns.
    """

    # Base optimal hours by user type
    DEFAULT_BUYER_HOURS = (8, 21)  # 8 AM - 9 PM
    DEFAULT_SELLER_HOURS = (7, 22)  # 7 AM - 10 PM

    # Peak engagement windows
    PEAK_WINDOWS = {
        'morning': (7, 9),
        'lunch': (11, 13),
        'afternoon': (15, 17),
        'evening': (19, 21),
    }

    def get_optimal_delivery_time(
        self,
        user,
        trigger_type: str = None,
        priority: int = 1,
        urgency: str = 'normal',
        context: Dict = None,
    ) -> Optional[datetime]:
        """
        Get the optimal delivery time for a notification.
        
        Args:
            user: The target user
            trigger_type: Notification trigger type
            priority: Priority level (0-3)
            urgency: 'low', 'normal', 'high', 'urgent'
            context: Additional context
            
        Returns:
            Optimal datetime for delivery, or immediately if urgent
        """
        from engagement.models import (
            UserBehaviorProfile, QuietHoursConfig,
            NotificationCooldown, NotificationAnalytics
        )

        now = timezone.now()

        # Urgent notifications send immediately
        if urgency == 'urgent' or priority >= 3:
            return now

        # Get user profile and configs
        profile, _ = UserBehaviorProfile.objects.get_or_create(user=user)
        quiet_config, _ = QuietHoursConfig.objects.get_or_create(user=user)

        # Get user's optimal hours
        user_hours = self._get_user_optimal_hours(profile, quiet_config, user.role)

        # Check if we're in quiet hours
        if self._is_quiet_hours(now, quiet_config, profile):
            # Schedule for after quiet hours
            return self._schedule_after_quiet_hours(now, quiet_config, profile)

        # Check if we're in optimal hours
        current_hour = now.hour
        if current_hour < user_hours[0] or current_hour > user_hours[1]:
            # Outside optimal hours, schedule for next optimal window
            return self._schedule_next_optimal_time(now, user_hours)

        # High priority: deliver at next peak window (or now if in one)
        if priority >= 2:
            if self._is_in_peak_window(current_hour):
                return now
            next_peak = self._get_next_peak_window(now, current_hour)
            return next_peak if next_peak else now

        # Normal priority: use AI-optimized timing
        # Check user's historical best performing hour
        best_hour = self._get_best_performing_hour(user, profile)

        if best_hour is not None:
            # Schedule for the best performing hour today
            return self._schedule_for_hour_today(now, best_hour, user_hours)

        # Default: schedule for next peak window
        if self._is_in_peak_window(current_hour):
            return now

        next_peak = self._get_next_peak_window(now, current_hour)
        return next_peak if next_peak else now + timedelta(minutes=30)

    def get_batch_delivery_times(self, users, base_time: datetime = None) -> Dict[int, datetime]:
        """
        Get optimal delivery times for a batch of users.
        Used for campaign scheduling to avoid simultaneous delivery spikes.
        
        Args:
            users: Iterable of users
            base_time: Base time to start scheduling from
            
        Returns:
            Dict mapping user_id to optimal delivery datetime
        """
        base_time = base_time or timezone.now()
        times = {}

        # Stagger delivery times to avoid server spikes
        stagger_interval = timedelta(seconds=2)

        for i, user in enumerate(users):
            opt_time = self.get_optimal_delivery_time(user, priority=1)
            if opt_time:
                # Add slight stagger
                staggered = opt_time + (stagger_interval * (i % 100))
                times[user.id] = staggered
            else:
                times[user.id] = base_time + (stagger_interval * (i % 100))

        return times

    def _get_user_optimal_hours(self, profile, quiet_config, role: str) -> tuple:
        """Get user's optimal notification hours."""
        # Prefer AI-learned quiet hours
        if quiet_config.ai_quiet_hours_start and quiet_config.ai_quiet_hours_end:
            return (quiet_config.ai_quiet_hours_start.hour, quiet_config.ai_quiet_hours_end.hour)

        # Use user's preferred hours from profile
        if profile.preferred_hour_start and profile.preferred_hour_end:
            return (profile.preferred_hour_start, profile.preferred_hour_end)

        # Default by role
        if role == 'seller':
            return self.DEFAULT_SELLER_HOURS
        return self.DEFAULT_BUYER_HOURS

    def _is_quiet_hours(self, current_time: datetime, quiet_config, profile) -> bool:
        """Check if current time is within quiet hours."""
        current_hour = current_time.hour
        current_minutes = current_time.minute + current_hour * 60

        # Check manual quiet hours
        if quiet_config.quiet_hours_start and quiet_config.quiet_hours_end:
            start_minutes = quiet_config.quiet_hours_start.hour * 60 + quiet_config.quiet_hours_start.minute
            end_minutes = quiet_config.quiet_hours_end.hour * 60 + quiet_config.quiet_hours_end.minute
            
            if start_minutes <= end_minutes:
                if start_minutes <= current_minutes <= end_minutes:
                    return True
            else:
                # Overnight quiet hours (e.g., 22:00 - 08:00)
                if current_minutes >= start_minutes or current_minutes <= end_minutes:
                    return True

        # Check night mode
        if quiet_config.reduce_at_night:
            night_start = quiet_config.night_hour_start if quiet_config.night_hour_start is not None else 21
            night_end = quiet_config.night_hour_end if quiet_config.night_hour_end is not None else 8
            if current_hour >= night_start or current_hour < night_end:
                return True

        # Check weekend quiet mode
        if quiet_config.weekend_quiet_mode and current_time.weekday() >= 5:
            if current_hour < 9 or current_hour > 20:
                return True

        return False

    def _schedule_after_quiet_hours(self, now: datetime, quiet_config, profile) -> datetime:
        """Schedule notification for after quiet hours end."""
        if quiet_config.quiet_hours_end:
            scheduled = now.replace(
                hour=quiet_config.quiet_hours_end.hour,
                minute=quiet_config.quiet_hours_end.minute + 5,  # 5 min buffer
                second=0, microsecond=0
            )
        elif quiet_config.night_hour_end:
            scheduled = now.replace(
                hour=quiet_config.night_hour_end,
                minute=5, second=0, microsecond=0
            )
        else:
            scheduled = now.replace(hour=9, minute=0, second=0, microsecond=0)

        # If scheduled time is already past, add a day
        if scheduled <= now:
            scheduled += timedelta(days=1)

        return scheduled

    def _schedule_next_optimal_time(self, now: datetime, user_hours: tuple) -> datetime:
        """Schedule for the next optimal time window."""
        start_hour = user_hours[0]
        
        # If we're before start hour, schedule for start hour today
        if now.hour < start_hour:
            scheduled = now.replace(hour=start_hour, minute=5, second=0, microsecond=0)
            if scheduled > now:
                return scheduled

        # Otherwise, schedule for start hour tomorrow
        tomorrow = now + timedelta(days=1)
        return tomorrow.replace(hour=start_hour, minute=5, second=0, microsecond=0)

    def _is_in_peak_window(self, hour: int) -> bool:
        """Check if current hour is in a peak engagement window."""
        for window_name, (start, end) in self.PEAK_WINDOWS.items():
            if start <= hour <= end:
                return True
        return False

    def _get_next_peak_window(self, now: datetime, current_hour: int) -> Optional[datetime]:
        """Get the next peak window datetime."""
        for window_name, (start, end) in self.PEAK_WINDOWS.items():
            if start > current_hour:
                return now.replace(hour=start, minute=0, second=0, microsecond=0)

        # No peak window left today, schedule for tomorrow morning
        tomorrow = now + timedelta(days=1)
        return tomorrow.replace(hour=7, minute=0, second=0, microsecond=0)

    def _get_best_performing_hour(self, user, profile) -> Optional[int]:
        """
        Get user's best performing notification hour based on historical data.
        Uses the optimal_notification_hour from the profile.
        """
        from engagement.models import NotificationAnalytics

        if profile.optimal_notification_hour:
            return profile.optimal_notification_hour

        # Try to derive from analytics
        recent_analytics = NotificationAnalytics.objects.filter(
            user=user,
            period='weekly',
        ).order_by('-period_start').first()

        if recent_analytics and recent_analytics.by_hour:
            by_hour = recent_analytics.by_hour
            if isinstance(by_hour, list) and len(by_hour) >= 24:
                # Find the hour with highest open rate
                best_hour = max(
                    range(24),
                    key=lambda h: by_hour[h] if isinstance(by_hour[h], (int, float)) else 0
                )
                return best_hour

        return None

    def _schedule_for_hour_today(self, now: datetime, target_hour: int, user_hours: tuple) -> datetime:
        """Schedule delivery for a specific hour today."""
        # Ensure target hour is within user's optimal hours
        hour = max(user_hours[0], min(target_hour, user_hours[1]))
        hour = max(0, min(23, hour))

        scheduled = now.replace(hour=hour, minute=0, second=0, microsecond=0)

        # If that time has passed, try next hour
        if scheduled <= now:
            if hour < 23:
                scheduled = scheduled + timedelta(hours=1)
            else:
                # Too late, schedule for tomorrow
                tomorrow = now + timedelta(days=1)
                scheduled = tomorrow.replace(hour=user_hours[0], minute=5, second=0, microsecond=0)

        return scheduled


# Singleton
_timing_engine = None


def get_timing_engine() -> TimingEngine:
    global _timing_engine
    if _timing_engine is None:
        _timing_engine = TimingEngine()
    return _timing_engine
