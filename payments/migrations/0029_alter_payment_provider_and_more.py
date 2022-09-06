# Generated by Django 4.1.1 on 2022-09-06 00:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0028_alter_payment_fee'),
    ]

    operations = [
        migrations.AlterField(
            model_name='payment',
            name='provider',
            field=models.SmallIntegerField(choices=[(0, 'paypal'), (1, 'stripe'), (2, 'crypto')], default=None),
        ),
        migrations.AlterField(
            model_name='paymentprovider',
            name='provider',
            field=models.SmallIntegerField(choices=[(0, 'paypal'), (1, 'stripe'), (2, 'crypto')], default=None),
        ),
        migrations.AlterField(
            model_name='paymentsession',
            name='provider',
            field=models.SmallIntegerField(choices=[(0, 'paypal'), (1, 'stripe'), (2, 'crypto')], default=None),
        ),
    ]
