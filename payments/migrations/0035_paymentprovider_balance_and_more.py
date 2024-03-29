# Generated by Django 4.1.1 on 2022-10-14 14:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0034_remove_payment_idempotency_key_remove_payment_status_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentprovider',
            name='balance',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=8, null=True),
        ),
        migrations.AlterField(
            model_name='paymentprovider',
            name='provider',
            field=models.SmallIntegerField(choices=[(0, 'paypal'), (1, 'stripe'), (2, 'bitcoin')], default=None),
        ),
    ]
