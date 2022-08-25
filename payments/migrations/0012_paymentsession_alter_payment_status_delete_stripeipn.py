# Generated by Django 4.0.2 on 2022-07-28 15:04

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0019_order_total'),
        ('payments', '0011_payment_provider_data'),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('provider', models.SmallIntegerField(choices=[(0, 'paypal'), (1, 'stripe')], default=None)),
                ('provider_data', models.JSONField(blank=True, null=True)),
                ('status', models.SmallIntegerField(choices=[(-2, 'error'), (-1, 'canceled'), (0, 'pending'), (1, 'authorized'), (2, 'requires more')], default=0)),
                ('idempotency_key', models.CharField(blank=True, max_length=255, null=True)),
                ('order', models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, to='orders.order')),
            ],
            options={
                'db_table': 'payment_session',
            },
        ),
        migrations.AlterField(
            model_name='payment',
            name='status',
            field=models.SmallIntegerField(choices=[(-3, 'refunded'), (-2, 'paritally refunded'), (-1, 'canceled'), (0, 'not paid'), (1, 'awaiting'), (2, 'requires action'), (3, 'captured')], default=0),
        ),
        migrations.DeleteModel(
            name='StripeIpn',
        ),
    ]
