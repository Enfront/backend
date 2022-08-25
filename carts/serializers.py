from django.utils import timezone

from rest_framework import serializers

from .models import Cart, CartItem

from products.models import Product


class CartItemSerializer(serializers.ModelSerializer):
    def create(self, validated_data, **kwargs):
        cart_item, created = CartItem.objects.get_or_create(
            cart=kwargs.get('cart'),
            product=kwargs.get('product'),
            expires_at__gt=timezone.now(),
            defaults={
                'cart': kwargs.get('cart'),
                'product': kwargs.get('product')
            }
        )

        if not created:
            cart_item.quantity = cart_item.quantity + 1
            cart_item.save()

    class Meta:
        model = CartItem
        fields = '__all__'
