# Generated by Django 4.0.2 on 2022-03-17 22:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0003_alter_coinpaymentsorder_currency_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='coinpaymentsorder',
            name='timeout',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
