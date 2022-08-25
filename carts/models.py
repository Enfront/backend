from django.db import models
from django.utils import timezone

from datetime import timedelta
from uuid import uuid4

from shared.models import TimestampedModel
from shops.models import Shop
from products.models import Product


def get_cart_expire_date():
    return timezone.now() + timedelta(days=7)


class Cart(TimestampedModel):
    user = models.UUIDField()
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
    ref_id = models.UUIDField(default=uuid4, editable=False, unique=True)

    class Meta:
        db_table = 'cart'


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=get_cart_expire_date)

    class Meta:
        db_table = 'cart_item'
