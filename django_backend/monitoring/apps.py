"""
Monitoring app configuration for Warungio Marketplace.
"""
from django.apps import AppConfig


class MonitoringConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'monitoring'
    verbose_name = 'Server Monitoring'
    label = 'monitoring'
