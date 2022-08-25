# Generated by Django 4.0.2 on 2022-08-17 15:23

import django.core.validators
from django.db import migrations, models


def change_price(apps, schema_editor):
    product_model = apps.get_model('products', 'Product')
    for product in product_model.objects.all():
        product.price = product.price * 100
        product.save()


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0005_alter_product_name_alter_product_slug'),
    ]

    operations = [
        migrations.RunPython(change_price),
        migrations.AlterField(
            model_name='product',
            name='price',
            field=models.BigIntegerField(validators=[django.core.validators.MinValueValidator(0.49), django.core.validators.MaxValueValidator(99999.99)]),
        ),
    ]
