# Generated by Django 4.1.1 on 2022-09-13 16:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0032_alter_paymentcrypto_btcpay_data'),
    ]

    operations = [
        migrations.DeleteModel(
            name='PaymentCrypto',
        ),
    ]
