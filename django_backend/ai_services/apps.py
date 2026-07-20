"""
AI Services App Configuration for Warungio Marketplace.
"""

from django.apps import AppConfig


class AIServicesConfig(AppConfig):
    """Configuration for the AI Services app."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ai_services'
    verbose_name = 'AI Services (Vertex AI / Gemini)'
