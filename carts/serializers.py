from django.utils import timezone
from rest_framework import serializers

from .models import Cart, CartItem

from products.models import Product


class CartItemSerializer(serializers.ModelSerializer):
    cart = serializers.UUIDField()
    product = serializers.UUIDField()

    def get_cart(self, cart_ref):
        try:
            return Cart.objects.get(ref_id=cart_ref)
        except Cart.DoesNotExist:
            raise CustomException(
                'Cart with id ' + str(cart_ref) + ' could not be found.',
                status.HTTP_404_NOT_FOUND
            )

    def get_product(self, product_ref):
        try:
            return Product.objects.get(ref_id=product_ref)
        except Product.DoesNotExist:
            raise CustomException(
                'Product with id ' + str(product_ref) + ' could not be found.',
                status.HTTP_404_NOT_FOUND
            )

    def create(self, validated_data):
        product = self.get_product(validated_data.get('product'))
        cart = self.get_cart(validated_data.get('cart'))

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            expires_at__gt=timezone.now(),

            defaults={
                'cart': cart,
                'product': product
            }
        )

        # make sure we adhere to the order minimums
        if created:
            cart_item.quantity = product.min_order_quantity
            cart_item.save()

        # make sure we adhere to the order maximums
        if not created and cart_item.quantity < product.max_order_quantity:

            # check to see if the amount at the minimum
            if cart_item.quantity < product.min_order_quantity:
                cart_item.quantity = product.min_order_quantity
                cart_item.save()

            # the item is already in a cart so just add 1 to the quantity
            cart_item.quantity = cart_item.quantity + 1
            cart_item.save()

    class Meta:
        model = CartItem
        fields = '__all__'
