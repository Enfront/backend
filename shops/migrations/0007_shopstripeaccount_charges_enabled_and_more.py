# Generated by Django 4.0.2 on 2022-07-19 22:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shops', '0006_alter_shopstripeaccount_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='shopstripeaccount',
            name='charges_enabled',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='shopstripeaccount',
            name='details_submitted',
            field=models.BooleanField(default=False),
        ),
    ]
