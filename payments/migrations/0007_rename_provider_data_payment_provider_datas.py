# Generated by Django 4.0.2 on 2022-07-27 21:53

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0006_stripeipn_payment'),
    ]

    operations = [
        migrations.RenameField(
            model_name='payment',
            old_name='provider_data',
            new_name='provider_datas',
        ),
    ]
