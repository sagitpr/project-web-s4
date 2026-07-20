"""
AI Intelligence Platform App Configuration.
Central orchestrator for all AI services across Warungio.
"""

from django.apps import AppConfig


class AIIntelligenceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ai_intelligence'
    verbose_name = 'AI Intelligence Platform'

    def ready(self):
        """Register Celery tasks and connect signals on startup."""
        import ai_intelligence.tasks  # noqa: F401
        from ai_intelligence import signals
        signals.connect_all()
