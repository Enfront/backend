# Generated by Django 4.0.2 on 2022-06-05 22:39

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('shops', '0003_shopcryptoaddresses'),
        ('customers', '0008_alter_customer_username'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customer',
            name='shop',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='shops.shop'),
        ),
    ]
