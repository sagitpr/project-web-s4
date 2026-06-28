import uuid
import logging
from decimal import Decimal

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator

logger = logging.getLogger('django_backend.orders')


class Order(models.Model):
    """
    Order model — minimal version for payment integration.
    Will be expanded with full cart/checkout flow later.
    """
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PAID = 'paid', 'Paid'
        PROCESSING = 'processing', 'Processing'
        SHIPPED = 'shipped', 'Shipped'
        DELIVERED = 'delivered', 'Delivered'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
        REFUNDED = 'refunded', 'Refunded'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders',
    )
    total_price = models.DecimalField(
        max_digits=14, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    status = models.CharField(
        max_length=20, choices=Status.choices,
        default=Status.PENDING, db_index=True,
    )
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        ordering = ['-created_at']

    def __str__(self):
        return f'Order {self.id} — {self.get_status_display()}'

    def mark_paid(self):
        """Transition to paid status."""
        if self.status in (self.Status.PENDING,):
            self.status = self.Status.PAID
            self.save(update_fields=['status', 'updated_at'])
            logger.info('Order %s marked as PAID', self.id)
