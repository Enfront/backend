# Generated by Django 4.0.2 on 2022-06-08 15:10

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('customers', '0011_alter_customer_first_name_alter_customer_last_name_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='customernote',
            name='status',
            field=models.SmallIntegerField(choices=[(-1, 'deleted'), (0, 'posted')], default=0),
        ),
        migrations.AddField(
            model_name='customernote',
            name='user',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
    ]
