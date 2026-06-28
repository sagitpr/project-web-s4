from django.apps import AppConfig


class OrdersConfig(AppConfig):
    name = 'orders'

    def ready(self):
        """
        Import and register Celery tasks on Django startup.
        Ensures @shared_task decorated functions are discovered by the
        Celery worker and signals are connected.
        """
        import orders.tasks  # noqa: F401 — registers Celery tasks
