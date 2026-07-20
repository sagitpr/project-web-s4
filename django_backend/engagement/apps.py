"""
Engagement & Retention Engine App Configuration.
"""

from django.apps import AppConfig


class EngagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'engagement'
    verbose_name = 'AI Engagement & Retention Engine'

    def ready(self):
        """Register Celery tasks and connect signals on startup."""
        import engagement.tasks  # noqa: F401
        from engagement import signals
        signals.connect_all()
