# Generated by Django 4.0.2 on 2022-06-05 00:38

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('customers', '0005_alter_customer_email'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Customer',
        ),
    ]
