# Generated by Django 4.1.1 on 2022-11-03 22:39

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('blacklists', '0004_blacklist_note'),
    ]

    operations = [
        migrations.AddField(
            model_name='blacklist',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='blacklist',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
