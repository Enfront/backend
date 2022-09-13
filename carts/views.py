from django.shortcuts import render
from django.utils import timezone
from django.http import HttpResponseRedirect
from django.utils.text import slugify
from django.core.exceptions import BadRequest

from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response

from uuid import uuid4

import os

from .models import Cart, CartItem
from .serializers import CartItemSerializer

from shared.exceptions import CustomException
from shared.services import get_url
from products.serializers import PublicProductCartSerializer
from products.models import Product
from shops.models import Shop


def get_users_cart(cart_ref):
    try:
        return Cart.objects.get(ref_id=cart_ref)
    except Cart.DoesNotExist:
        return None


def get_users_cart_items(cart):
    detailed_cart_items = []
    cart_items = CartItem.objects.filter(cart=cart, quantity__gt=0, expires_at__gt=timezone.now())

    for cart_item in cart_items:
        product = Product.objects.get(id=cart_item.product_id)
        setattr(product, 'quantity', cart_item.quantity)
        setattr(product, 'cart_ref_id', cart.ref_id)

        product_data = PublicProductCartSerializer(product).data
        detailed_cart_items.append(product_data)

    return detailed_cart_items


def get_cart_total(cart_items):
    total = 0
    for cart_item in cart_items:
        total += cart_item['price'] * cart_item['quantity']

    return total


def delete_cart_item(cart_id, item_id):
    try:
        item = CartItem.objects.get(
            cart_id=cart_id,
            product__ref_id=item_id,
            quantity__gt=0,
            expires_at__gt=timezone.now()
        )
    except CartItem.DoesNotExist:
        raise CustomException(
            'A product with id ' + str(item_id) + ' could not be found in a cart with ID ' + str(cart_id) + '.',
            status.HTTP_404_NOT_FOUND,
        )

    item.quantity = 0
    item.expires_at = timezone.now()
    item.save()


class CartView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        cart_cookie = request.COOKIES.get('_enfront_cid')

        cart = get_users_cart(cart_cookie)
        cart_items = get_users_cart_items(cart)
        total = get_cart_total(cart_items)

        products = PublicProductCartSerializer(instance=cart_items, many=True).data

        cart_info = {
            'cart_items': products,
            'total': total,
        }

        data = {
            'success': True,
            'message': 'Cart info that matches your criteria was found.',
            'data': cart_info
        }

        return Response(data, status=status.HTTP_200_OK)


class CartAddItemView(APIView):
    permission_classes = [AllowAny]

    def create_cart(self, shop_url, user_ref):
        try:
            shop = Shop.objects.get(domain=shop_url)
        except Shop.DoesNotExist:
            raise CustomException(
                'Shop could not be found.',
                status.HTTP_404_NOT_FOUND
            )

        cart_uuid = uuid4()
        if user_ref is None:
            user_ref = uuid4()

        return Cart.objects.create(shop=shop, user=user_ref, ref_id=cart_uuid)

    def post(self, request):
        cart_data = request.data
        cart_cookie = request.COOKIES.get('_enfront_cid')
        user_cookie = request.COOKIES.get('_enfront_uid')
        new_cart = False

        if cart_data.get('product') is None:
            raise CustomException(
                'Product id is required.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        cart = get_users_cart(cart_cookie)
        if cart is None:
            cart = self.create_cart(request.get_host(), user_cookie)
            new_cart = True

        cart_item_details = {
            'product': cart_data.get('product'),
            'quantity': cart_data.get('quantity', 1),
            'cart': cart.ref_id,
        }

        context = {'request': request}
        serialized_data = CartItemSerializer(data=cart_item_details, context=context)
        is_valid = serialized_data.is_valid(raise_exception=True)

        if not is_valid:
            raise CustomException(
                'There was a problem adding a product to the cart.',
                status.HTTP_400_BAD_REQUEST
            )

        serialized_data.create(serialized_data.data)

        response = HttpResponseRedirect(get_url('/cart', slugify(cart_data.get('shop'))))

        # create cart cookie since there is not one already
        if new_cart:
            response.set_cookie('_enfront_cid', cart.ref_id, 604800)

        return response


class CartRemoveItemView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        cart_data = request.data
        cart_cookie = request.COOKIES.get('_enfront_cid')

        try:
            product = Product.objects.get(ref_id=cart_data.get('product'))
        except Product.DoesNotExist:
            raise CustomException(
                'Product with ID ' + str(cart_data.get('product')) + ' could not be found.',
                status.HTTP_404_NOT_FOUND
            )

        try:
            cart = get_users_cart(cart_cookie)

            cart_item = CartItem.objects.get(
                cart=cart,
                product=product,
                quantity__gt=0,
                expires_at__gt=timezone.now()
            )

            if cart_item.quantity > 1 and cart_item.quantity - 1 >= product.min_order_quantity:
                cart_item.quantity = cart_item.quantity - 1
                cart_item.save()
            else:
                # don't actually delete; just change expiration date and quantity to 0
                cart_item.quantity = 0
                cart_item.expires_at = timezone.now()
                cart_item.save()

        except BadRequest:
            raise CustomException(
                'There was a problem deleting your cart item.',
                status.HTTP_400_BAD_REQUEST,
            )

        return HttpResponseRedirect(get_url('/cart', slugify(cart_data.get('shop'))))
