# Generated by Django 4.0.2 on 2022-06-05 00:38

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('shops', '0003_shopcryptoaddresses'),
        ('customers', '0006_delete_customer'),
    ]

    operations = [
        migrations.CreateModel(
            name='Customer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('email', models.EmailField(max_length=254)),
                ('username', models.CharField(max_length=255, unique=True)),
                ('first_name', models.CharField(max_length=255)),
                ('last_name', models.CharField(max_length=255)),
                ('is_active', models.BooleanField(default=False)),
                ('last_login', models.DateTimeField(default=django.utils.timezone.now)),
                ('ref_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('shop', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='shops.shop')),
            ],
            options={
                'db_table': 'customers',
            },
        ),
    ]
