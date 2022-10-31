from django.db import models

from uuid import uuid4

from users.models import User
from countries.models import Country


class Shop(models.Model):
    DELETED = -1
    INACTIVE = 0
    ACTIVE = 1

    STATUS_CHOICES = (
        (DELETED, 'Deleted'),
        (INACTIVE, 'Inactive'),
        (ACTIVE, 'Active'),
    )

    name = models.CharField(max_length=255)
    email = models.EmailField()
    status = models.SmallIntegerField(choices=STATUS_CHOICES, default=INACTIVE)
    currency = models.CharField(max_length=3, default='USD')
    owner = models.ForeignKey(User, on_delete=models.SET(INACTIVE), blank=True)
    domain = models.URLField(unique=True, blank=True)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    description = models.TextField(default='We sell...')
    ref_id = models.UUIDField(default=uuid4, editable=False, unique=True)

    class Meta:
        db_table = 'shop'
