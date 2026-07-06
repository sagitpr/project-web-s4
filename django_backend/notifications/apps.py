from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    name = 'notifications'

    def ready(self):
        """Connect notification signals on app startup."""
        from .signals import connect_all
        connect_all()
