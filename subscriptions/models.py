from django.db import models


from uuid import uuid4

from users.models import User
from shared.models import TimestampedModel


class Subscription(TimestampedModel):
    PAYPAL = 0
    STRIPE = 1

    PROVIDER_CHOICES = (
        (PAYPAL, 'paypal'),
        (STRIPE, 'stripe'),
    )

    TIER_ONE = 1
    TIER_TWO = 2
    TIER_THREE = 3

    TIER_CHOICES = (
        (TIER_ONE, 'tier one'),
        (TIER_TWO, 'tier two'),
        (TIER_THREE, 'tier three'),
    )

    CANCELED = -1
    NOT_PAID = 0
    SUBSCRIBED = 1

    STATUS_CHOICES = (
        (CANCELED, 'canceled'),
        (NOT_PAID, 'not paid'),
        (SUBSCRIBED, 'subscribed'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True)
    started_at = models.DateTimeField(blank=True, null=True)
    canceled_at = models.DateTimeField(blank=True, null=True)
    provider = models.SmallIntegerField(choices=PROVIDER_CHOICES, default=None)
    provider_data = models.JSONField(blank=True, null=True)
    status = models.SmallIntegerField(choices=STATUS_CHOICES, default=NOT_PAID)
    subscription_tier = models.SmallIntegerField(choices=TIER_CHOICES, null=True)
    ref_id = models.UUIDField(default=uuid4, editable=False, unique=True, null=True)
    idempotency_key = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'subscription'


class SubscriptionPayment(TimestampedModel):
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

    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True)
    provider = models.SmallIntegerField(choices=PROVIDER_CHOICES, default=None)
    provider_data = models.JSONField(blank=True, null=True)
    status = models.SmallIntegerField(choices=STATUS_CHOICES, default=NOT_PAID)
    ref_id = models.UUIDField(default=uuid4, editable=False, unique=True, null=True)

    class Meta:
        db_table = 'subscription_payment'
