# Generated by Django 4.0.2 on 2022-06-06 03:04

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_user_is_owner_user_subscription_tier_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='is_owner',
        ),
    ]
