from django.db import models

from uuid import uuid4

from shared.models import TimestampedModel
from shops.models import Shop


class Payout(TimestampedModel):
    DENIED = -1
    REQUESTED = 0
    PENDING = 1
    COMPLETED = 2

    STATUS_CHOICES = (
        (DENIED, 'denied'),
        (REQUESTED, 'requested'),
        (PENDING, 'pending'),
        (COMPLETED, 'completed'),
    )

    destination = models.CharField(max_length=72)
    amount = models.DecimalField(max_digits=10, decimal_places=8)
    currency = models.CharField(max_length=3, default='BTC')
    provider_data = models.JSONField(blank=True, null=True)
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
    status = models.SmallIntegerField(choices=STATUS_CHOICES, default=REQUESTED)
    ref_id = models.UUIDField(default=uuid4, editable=False, unique=True)

    class Meta:
        db_table = 'payout'
