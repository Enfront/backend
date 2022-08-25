from django.db import models


class Country(models.Model):
    num_code = models.SmallIntegerField()
    iso_2 = models.CharField(max_length=2)
    iso_3 = models.CharField(max_length=3)
    name = models.CharField(max_length=255)
    continent = models.CharField(max_length=255)
    stripe_available = models.BooleanField(default=False)
    paypal_available = models.BooleanField(default=False)

    class Meta:
        db_table = 'country'

