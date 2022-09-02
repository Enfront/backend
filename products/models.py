from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from uuid import uuid4

from shared.models import TimestampedModel
from shops.models import Shop


class Product(TimestampedModel):
    VIRTUAL = 0
    PHYSICAL = 1

    TYPE_CHOICES = (
        (VIRTUAL, 'digital'),
        (PHYSICAL, 'physical'),
    )

    UNLISTED_OOS = -2
    DELETED = -1
    UNLISTED = 0
    LISTED = 1

    STATUS_CHOICES = (
        (UNLISTED_OOS, 'out of stock'),
        (DELETED, 'deleted'),
        (UNLISTED, 'unlisted'),
        (LISTED, 'listed'),
    )

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    stock = models.PositiveIntegerField(default=0, blank=True)
    type = models.SmallIntegerField(choices=TYPE_CHOICES, default=PHYSICAL)
    status = models.SmallIntegerField(choices=STATUS_CHOICES, default=UNLISTED)
    slug = models.SlugField(max_length=255, blank=True)
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
    ref_id = models.UUIDField(default=uuid4, editable=False, unique=True)
    price = models.BigIntegerField(validators=[MinValueValidator(49), MaxValueValidator(1000000)])
    min_order_quantity = models.PositiveIntegerField(default=1)
    max_order_quantity = models.PositiveIntegerField(default=2147483647)

    class Meta:
        db_table = 'product'


class DigitalProduct(TimestampedModel):
    DELETED = -1
    LISTED = 0
    PURCHASED = 1

    STATUS_CHOICES = (
        (DELETED, 'deleted'),
        (LISTED, 'listed'),
        (PURCHASED, 'purchased'),
    )

    key = models.CharField(max_length=99)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    recipient_email = models.EmailField(blank=True, null=True)
    status = models.SmallIntegerField(choices=STATUS_CHOICES, default=LISTED, blank=True)
    ref_id = models.UUIDField(default=uuid4, editable=False, unique=True)

    class Meta:
        db_table = 'product_digital'
