# Generated by Django 4.0.2 on 2022-09-02 16:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0012_alter_product_maximum_order_quantiy'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='maximum_order_quantiy',
            field=models.PositiveIntegerField(default=2147483647),
        ),
    ]
