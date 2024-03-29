# Generated by Django 4.0.2 on 2022-07-19 21:36

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('shops', '0004_shoppaypalaccount_email_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ShopStripeAccount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('account_id', models.CharField(max_length=255)),
                ('status', models.SmallIntegerField(choices=[(-1, 'inactive'), (1, 'active')], default=1)),
                ('shop', models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, to='shops.shop')),
            ],
            options={
                'ordering': ['-created_at', '-updated_at'],
                'abstract': False,
            },
        ),
    ]
