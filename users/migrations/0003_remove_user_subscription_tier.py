# Generated by Django 4.0.2 on 2022-04-22 22:48

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_user_subscription_tier'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='subscription_tier',
        ),
    ]
