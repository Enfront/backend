from django.utils.text import slugify
from rest_framework import serializers

from .models import Product, DigitalProduct

from shops.models import Shop
from file_uploads.models import FileData
from file_uploads.serializers import PublicImageSerializer


class ProductSerializer(serializers.ModelSerializer):
    shop = serializers.UUIDField()
    slug = serializers.SerializerMethodField()

    def get_shop(self, ref_id):
        return Shop.objects.get(ref_id=ref_id)

    def get_slug(self, name):
        return slugify(name)

    def create(self, validated_data):
        validated_data['shop'] = self.get_shop(validated_data.get('shop'))
        validated_data['slug'] = self.get_slug(validated_data.get('name'))
        product = Product.objects.create(**validated_data)

        return product

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name')
        instance.description = validated_data.get('description')
        instance.status = validated_data.get('status')
        instance.slug = self.get_slug(validated_data.get('name'))
        instance.shop = self.get_shop(validated_data.get('shop'))
        instance.price = validated_data.get('price')
        instance.min_order_quantity = validated_data.get('min_order_quantity')
        instance.max_order_quantity = validated_data.get('max_order_quantity')
        instance.save()

        return instance

    class Meta:
        model = Product
        fields = '__all__'


class PublicDigitalProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = DigitalProduct
        fields = ['created_at', 'key', 'recipient_email', 'status', 'ref_id']


class PublicProductSerializer(serializers.ModelSerializer):
    images = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    available = serializers.SerializerMethodField()
    max_order_quantity = serializers.SerializerMethodField()

    def get_images(self, request):
        images = FileData.objects.filter(itemimage__item_id=request.id).exclude(status=-1)
        image_data = PublicImageSerializer(instance=images, many=True).data

        return image_data

    def get_price(self, request):
        return request.price

    def get_available(self, request):
        if request.stock == 0 or request.status <= 0:
            return False

        return True

    def get_max_order_quantity(self, request):
        if request.max_order_quantity > request.stock:
            return request.stock

        return request.max_order_quantity

    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'slug', 'images', 'available', 'min_order_quantity',
                  'max_order_quantity', 'ref_id', 'stock']


class PublicProductOwnerSerializer(serializers.ModelSerializer):
    images = serializers.SerializerMethodField()
    keys = serializers.SerializerMethodField()

    def get_images(self, request):
        images = FileData.objects.filter(itemimage__item_id=request.id).exclude(status=-1)
        image_data = PublicImageSerializer(instance=images, many=True).data

        return image_data

    def get_keys(self, request):
        keys = DigitalProduct.objects.filter(product=request.id, status=0)
        key_data = PublicDigitalProductSerializer(instance=keys, many=True).data

        return key_data

    class Meta:
        model = Product
        fields = ['name', 'description', 'stock', 'status', 'slug', 'ref_id', 'price', 'images', 'keys',
                  'min_order_quantity', 'max_order_quantity']


class PublicProductCartSerializer(PublicProductSerializer):
    quantity = serializers.SerializerMethodField()
    cart_ref_id = serializers.SerializerMethodField()

    def get_quantity(self, request):
        return request.quantity

    def get_cart_ref_id(self, request):
        return request.cart_ref_id

    class Meta:
        model = Product
        fields = ['name', 'price', 'quantity', 'stock', 'slug', 'images', 'ref_id', 'cart_ref_id', 'min_order_quantity',
                  'max_order_quantity']
