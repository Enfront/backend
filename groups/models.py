from django.db import models

from uuid import uuid4

from products.models import Product
from shared.models import TimestampedModel
from shops.models import Shop


class Collection(TimestampedModel):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=False)
    products = models.ManyToManyField(Product, db_table='collection_products_map')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
    ref_id = models.UUIDField(default=uuid4, editable=False, unique=True)

    class Meta:
        db_table = 'collection'
