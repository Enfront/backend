# Generated by Django 4.1.1 on 2022-11-11 16:33

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('products', '0015_alter_product_price'),
        ('shops', '0011_shop_description'),
    ]

    operations = [
        migrations.CreateModel(
            name='Collection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(max_length=255)),
                ('slug', models.SlugField()),
                ('ref_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('products', models.ManyToManyField(db_table='collection_products_map', to='products.product')),
                ('shop', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='shops.shop')),
            ],
            options={
                'db_table': 'collection',
            },
        ),
    ]
