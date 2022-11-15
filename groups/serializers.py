from rest_framework import serializers

from .models import Collection

from products.models import Product
from products.serializers import PublicProductSerializer
from shops.models import Shop


class CollectionSerializer(serializers.ModelSerializer):
    shop = serializers.UUIDField()
    products = serializers.ListField(child=serializers.UUIDField())

    def get_shop(self, shop_ref):
        return Shop.objects.get(ref_id=shop_ref)

    def create(self, validated_data):
        products = validated_data['products']
        validated_data.pop('products', None)

        validated_data['shop'] = self.get_shop(validated_data['shop'])
        collection = Collection.objects.create(**validated_data)

        for product in products:
            product_instance = Product.objects.get(ref_id=product)
            collection.products.add(product_instance)

        return collection.ref_id

    def partial_update(self, instance, validated_data):
        instance.title = validated_data['title']
        instance.slug = validated_data['slug']

        product_ids = []
        for product in validated_data['products']:
            product_instance = Product.objects.get(ref_id=product)
            product_ids.append(product_instance.id)

        instance.products.set(product_ids)
        instance.save()

        return instance

    class Meta:
        model = Collection
        fields = '__all__'


class PublicCollectionSerializer(serializers.ModelSerializer):
    products = serializers.SerializerMethodField()

    def get_products(self, collection):
        return PublicProductSerializer(collection.products, many=True).data

    class Meta:
        model = Collection
        fields = ['ref_id', 'title', 'slug', 'products', 'created_at', 'updated_at', 'products']
