from django.db import models

from uuid import uuid4

from shared.models import TimestampedModel
from orders.models import Order
from shops.models import Shop


class Payment(TimestampedModel):
    PAYPAL = 0
    STRIPE = 1

    PROVIDER_CHOICES = (
        (PAYPAL, 'paypal'),
        (STRIPE, 'stripe'),
    )

    REFUNDED = -3
    PARTIALLY_REFUNDED = -2
    CANCELED = -1
    NOT_PAID = 0
    AWAITING = 1
    REQUIRES_ACTION = 2
    CAPTURED = 3

    STATUS_CHOICES = (
        (REFUNDED, 'refunded'),
        (PARTIALLY_REFUNDED, 'paritally refunded'),
        (CANCELED, 'canceled'),
        (NOT_PAID, 'not paid'),
        (AWAITING, 'awaiting'),
        (REQUIRES_ACTION, 'requires action'),
        (CAPTURED, 'captured'),
    )

    order = models.ForeignKey(Order, on_delete=models.CASCADE, blank=True)
    captured_at = models.DateTimeField(blank=True, null=True)
    canceled_at = models.DateTimeField(blank=True, null=True)
    provider = models.SmallIntegerField(choices=PROVIDER_CHOICES, default=None)
    provider_data = models.JSONField(blank=True, null=True)
    fee = models.BigIntegerField(default=0)
    status = models.SmallIntegerField(choices=STATUS_CHOICES, default=NOT_PAID)
    ref_id = models.UUIDField(default=uuid4, editable=False, unique=True, null=True)
    idempotency_key = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'payment'


class PaymentSession(TimestampedModel):
    PAYPAL = 0
    STRIPE = 1

    PROVIDER_CHOICES = (
        (PAYPAL, 'paypal'),
        (STRIPE, 'stripe'),
    )

    ERROR = -2
    CANCELED = -1
    PENDING = 0
    REQUIRES_MORE = 1
    AUTHORIZED = 2

    STATUS_CHOICES = (
        (ERROR, 'error'),
        (CANCELED, 'canceled'),
        (PENDING, 'pending'),
        (REQUIRES_MORE, 'requires more'),
        (AUTHORIZED, 'authorized'),
    )

    order = models.ForeignKey(Order, on_delete=models.CASCADE, blank=True)
    provider = models.SmallIntegerField(choices=PROVIDER_CHOICES, default=None)
    provider_data = models.JSONField(blank=True, null=True)
    status = models.SmallIntegerField(choices=STATUS_CHOICES, default=PENDING)
    idempotency_key = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'payment_session'


class PaymentProvider(TimestampedModel):
    PAYPAL = 0
    STRIPE = 1

    PROVIDER_CHOICES = (
        (PAYPAL, 'paypal'),
        (STRIPE, 'stripe'),
    )

    INACTIVE = -1
    ACTIVE = 1

    STATUS = (
        (INACTIVE, 'inactive'),
        (ACTIVE, 'active'),
    )

    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, blank=True)
    provider = models.SmallIntegerField(choices=PROVIDER_CHOICES, default=None)
    provider_data = models.JSONField(blank=True)
    status = models.SmallIntegerField(choices=STATUS, default=ACTIVE)

    class Meta:
        db_table = 'payment_provider'
