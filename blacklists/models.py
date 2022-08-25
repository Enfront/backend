from django.db import models

from uuid import uuid4

from users.models import User
from shops.models import Shop


class Blacklist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    paypal_email = models.EmailField(blank=True, null=True)
    country = models.CharField(max_length=50, blank=True, null=True)
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, blank=True)
    ref_id = models.UUIDField(default=uuid4, editable=False, unique=True)

    class Meta:
        db_table = 'blacklist'
