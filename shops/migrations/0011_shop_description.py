# Generated by Django 4.0.2 on 2022-08-30 14:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shops', '0010_alter_shop_table'),
    ]

    operations = [
        migrations.AddField(
            model_name='shop',
            name='description',
            field=models.TextField(default='We sell...'),
        ),
    ]
