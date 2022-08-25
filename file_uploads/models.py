from django.db import models

from polymorphic.models import PolymorphicModel
from uuid import uuid4

from products.models import Product
from shared.models import TimestampedModel


# https://django-polymorphic.readthedocs.io/en/stable/quickstart.html#making-your-models-polymorphic
class FileData(PolymorphicModel, TimestampedModel):
    DELETED = -1
    LISTED = 1

    STATUS_CHOICES = [
        (DELETED, 'deleted'),
        (LISTED, 'listed')
    ]

    name = models.CharField(max_length=120)
    path = models.CharField(max_length=250)
    size = models.IntegerField()
    original_name = models.CharField(max_length=120)
    status = models.SmallIntegerField(choices=STATUS_CHOICES, default=LISTED, blank=True)
    ref_id = models.UUIDField(default=uuid4, editable=False, unique=True)

    class Meta:
        db_table = 'file_data'


class ItemImage(FileData):
    item = models.ForeignKey(Product, on_delete=models.CASCADE)

    class Meta:
        db_table = 'file_data_item_image'
