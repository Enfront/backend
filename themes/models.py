from django.db import models

from uuid import uuid4

from users.models import User
from shops.models import Shop
from shared.models import TimestampedModel


class Theme(TimestampedModel):
    PRIVATE = 0
    PUBLIC = 1

    STATUS_CHOICES = (
        (PRIVATE, 'private'),
        (PUBLIC, 'public')
    )

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    developer = models.ForeignKey(User, on_delete=models.CASCADE, blank=True)
    status = models.SmallIntegerField(choices=STATUS_CHOICES, default=PRIVATE)
    ref_id = models.UUIDField(default=uuid4, editable=False, unique=True)

    class Meta:
        db_table = 'theme'


class ThemeConfiguration(TimestampedModel):
    UNPUBLISHED = 0
    LIVE = 1

    STATUS_CHOICES = (
        (UNPUBLISHED, 'unpublished'),
        (LIVE, 'live')
    )

    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, blank=True)
    theme = models.ForeignKey(Theme, on_delete=models.CASCADE, blank=True)
    file_name = models.CharField(max_length=99, blank=True)
    status = models.SmallIntegerField(choices=STATUS_CHOICES, default=UNPUBLISHED, blank=True)
    config_status = models.SmallIntegerField(choices=STATUS_CHOICES, default=UNPUBLISHED, blank=True)
    ref_id = models.UUIDField(default=uuid4, editable=False, unique=True)

    class Meta:
        db_table = 'theme_configuration'
