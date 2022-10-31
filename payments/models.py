from django.db import models

from uuid import uuid4

from shared.models import TimestampedModel
from orders.models import Order
from shops.models import Shop


class Payment(TimestampedModel):
    PAYPAL = 0
    STRIPE = 1
    CRYPTO = 2

    PROVIDER_CHOICES = (
        (PAYPAL, 'paypal'),
        (STRIPE, 'stripe'),
        (CRYPTO, 'crypto'),
    )

    order = models.ForeignKey(Order, on_delete=models.CASCADE, blank=True)
    captured_at = models.DateTimeField(blank=True, null=True)
    canceled_at = models.DateTimeField(blank=True, null=True)
    provider = models.SmallIntegerField(choices=PROVIDER_CHOICES, default=None)
    provider_data = models.JSONField(blank=True, null=True)
    fee = models.BigIntegerField(default=0)
    ref_id = models.UUIDField(default=uuid4, editable=False, unique=True, null=True)

    class Meta:
        db_table = 'payment'


class PaymentSession(TimestampedModel):
    PAYPAL = 0
    STRIPE = 1
    CRYPTO = 2

    PROVIDER_CHOICES = (
        (PAYPAL, 'paypal'),
        (STRIPE, 'stripe'),
        (CRYPTO, 'crypto'),
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

    class Meta:
        db_table = 'payment_session'


class PaymentProvider(TimestampedModel):
    PAYPAL = 0
    STRIPE = 1
    BITCOIN = 2

    PROVIDER_CHOICES = (
        (PAYPAL, 'paypal'),
        (STRIPE, 'stripe'),
        (BITCOIN, 'bitcoin'),
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
    balance = models.DecimalField(blank=True, null=True, decimal_places=8, max_digits=10)
    status = models.SmallIntegerField(choices=STATUS, default=ACTIVE)

    class Meta:
        db_table = 'payment_provider'
