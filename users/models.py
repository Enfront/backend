from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin

from uuid import uuid4

from .managers import CustomUserManager

from shared.models import TimestampedModel


# Create your models here.
class User(AbstractBaseUser, PermissionsMixin, TimestampedModel):
    FREE = 0
    TIER_ONE = 1
    TIER_TWO = 2

    TIER_CHOICES = (
        (FREE, 'free'),
        (TIER_ONE, 'tier one'),
        (TIER_TWO, 'tier two'),
    )

    email = models.EmailField()
    username = models.CharField(max_length=255, blank=True, null=True)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    subscription_tier = models.SmallIntegerField(choices=TIER_CHOICES, default=FREE, blank=True)
    is_active = models.BooleanField(default=False)
    last_login = models.DateTimeField(default=timezone.now)
    ref_id = models.UUIDField(default=uuid4, editable=False, unique=True)

    USERNAME_FIELD = 'ref_id'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    class Meta:
        db_table = 'user'

    def __str__(self):
        return str(self.ref_id)
