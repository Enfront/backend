from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

from datetime import timedelta
from uuid import uuid4

from shared.models import TimestampedModel
from products.models import Product, DigitalProduct
from shops.models import Shop
from users.models import User
from customers.models import Customer


def get_order_expire_date():
    return timezone.now() + timedelta(days=1)


class OrderItem(models.Model):
    CANCELLED = -1
    PENDING = 0
    SHIPPED = 1
    DELIVERED = 2

    STATUS_CHOICES = (
        (CANCELLED, 'cancelled'),
        (PENDING, 'pending'),
        (SHIPPED, 'shipped'),
        (DELIVERED, 'delivered'),
    )

    quantity = models.PositiveIntegerField(default=0)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    purchased_keys = models.ManyToManyField(DigitalProduct, db_table='order_digital_items_map', blank=True)
    current_status = models.SmallIntegerField(choices=STATUS_CHOICES, default=PENDING)
    price = models.BigIntegerField(validators=[MinValueValidator(0.49), MaxValueValidator(99999.99)])

    class Meta:
        db_table = 'order_item'


class Order(TimestampedModel):
    CHARGEBACK_WON = -6
    CHARGEBACK_LOST = -5
    CHARGEBACK_PENDING = -4
    REFUNDED = -3
    DENIED = -2
    CANCELLED = -1
    WAITING_FOR_PAYMENT = 0
    PAYMENT_CONFIRMED = 1
    PENDING = 2
    COMPLETE = 3

    STATUS_CHOICES = (
        (CHARGEBACK_WON, 'chargeback won'),
        (CHARGEBACK_LOST, 'chargeback lost'),
        (CHARGEBACK_PENDING, 'chargeback pending'),
        (REFUNDED, 'refunded'),
        (DENIED, 'denied'),
        (CANCELLED, 'cancelled'),
        (WAITING_FOR_PAYMENT, 'waiting for payment'),
        (PAYMENT_CONFIRMED, 'payment confirmed'),
        (PENDING, 'pending'),
        (COMPLETE, 'complete'),
    )

    email = models.EmailField(unique=False, blank=True, null=True)
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, blank=True, null=True)
    currency = models.CharField(max_length=3, default='USD')
    items = models.ManyToManyField(OrderItem, db_table='order_items_map', blank=True)
    email_sent = models.BooleanField(default=False, blank=True)
    ref_id = models.UUIDField(default=uuid4, editable=False, unique=True)
    expires_at = models.DateTimeField(default=get_order_expire_date)
    total = models.BigIntegerField(blank=True)
    current_status = models.SmallIntegerField(
        choices=STATUS_CHOICES,
        default=WAITING_FOR_PAYMENT,
        blank=True,
        null=False
    )

    class Meta:
        db_table = 'order'


class OrderStatus(models.Model):
    CHARGEBACK_WON = -6
    CHARGEBACK_LOST = -5
    CHARGEBACK_PENDING = -4
    REFUNDED = -3
    DENIED = -2
    CANCELLED = -1
    WAITING_FOR_PAYMENT = 0
    PAYMENT_CONFIRMED = 1
    PENDING = 2
    COMPLETE = 3

    STATUS_CHOICES = (
        (CHARGEBACK_WON, 'chargeback won'),
        (CHARGEBACK_LOST, 'chargeback lost'),
        (CHARGEBACK_PENDING, 'chargeback pending'),
        (REFUNDED, 'refunded'),
        (DENIED, 'denied'),
        (CANCELLED, 'cancelled'),
        (WAITING_FOR_PAYMENT, 'waiting for payment'),
        (PAYMENT_CONFIRMED, 'payment confirmed'),
        (PENDING, 'pending'),
        (COMPLETE, 'complete'),
    )

    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    status = models.SmallIntegerField(choices=STATUS_CHOICES, default=WAITING_FOR_PAYMENT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'order_status'


class OrderItemStatus(models.Model):
    CANCELLED_OOS = -2
    CANCELLED = -1
    PENDING = 0
    SHIPPED = 1
    DELIVERED = 2

    STATUS_CHOICES = (
        (CANCELLED, 'cancelled'),
        (PENDING, 'pending'),
        (SHIPPED, 'shipped'),
        (DELIVERED, 'delivered'),
    )

    item = models.ForeignKey(OrderItem, on_delete=models.CASCADE)
    status = models.SmallIntegerField(choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'order_item_status'


class OrderUserData(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, blank=False, null=False)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    using_vpn = models.BooleanField(blank=True, null=False)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    city = models.CharField(max_length=50, blank=True, null=True)
    region = models.CharField(max_length=50, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=50, blank=True, null=True)
    browser = models.CharField(max_length=50, blank=True, null=True)
    os = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = 'order_user'


class OrderComment(TimestampedModel):
    DELETED = -1
    POSTED = 0

    STATUS_CHOICES = (
        (DELETED, 'deleted'),
        (POSTED, 'posted'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    comment = models.CharField(max_length=999)
    status = models.SmallIntegerField(choices=STATUS_CHOICES, default=POSTED)
    ref_id = models.UUIDField(default=uuid4, editable=False, unique=True)

    class Meta:
        db_table = 'order_comment'
