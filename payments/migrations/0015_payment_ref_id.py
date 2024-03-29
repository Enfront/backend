# Generated by Django 4.0.2 on 2022-08-08 15:35

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0014_paymentprovider_delete_paypalorder'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='ref_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, null=True, unique=True),
        ),
    ]
