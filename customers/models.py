from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin

from uuid import uuid4

from users.managers import CustomUserManager
from users.models import User
from shops.models import Shop
from shared.models import TimestampedModel


# Create your models here.
class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)

    class Meta:
        db_table = 'customer'


class CustomerNote(TimestampedModel):
    DELETED = -1
    POSTED = 0

    STATUS_CHOICES = (
        (DELETED, 'deleted'),
        (POSTED, 'posted'),
    )

    note = models.CharField(max_length=999)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.SmallIntegerField(choices=STATUS_CHOICES, default=POSTED)
    ref_id = models.UUIDField(default=uuid4, editable=False, unique=True)

    class Meta:
        db_table = 'customer_note'
