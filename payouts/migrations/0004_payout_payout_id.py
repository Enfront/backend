# Generated by Django 4.1.1 on 2022-10-14 18:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payouts', '0003_payout_shop'),
    ]

    operations = [
        migrations.AddField(
            model_name='payout',
            name='payout_id',
            field=models.CharField(default=123123, max_length=72),
            preserve_default=False,
        ),
    ]
