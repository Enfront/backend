# Generated by Django 4.0.2 on 2022-05-05 20:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('subscriptions', '0003_alter_paypalsubscription_next_billing_time'),
    ]

    operations = [
        migrations.AddField(
            model_name='paypalsubscription',
            name='event_type',
            field=models.CharField(default='BILLING.SUBSCRIPTION.ACTIVATED', max_length=255),
            preserve_default=False,
        ),
    ]
