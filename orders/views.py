from django.shortcuts import render
from django.utils import timezone
from django.http import HttpResponseRedirect
from django.db.models.functions import ExtractDay
from django.template.loader import render_to_string
from django.conf import settings
from django.db.models import Q

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from ipware import get_client_ip
from device_detector import SoftwareDetector
from datetime import timedelta

import decimal
import requests
import os

from .serializers import (
    OrderSerializer,
    OrderUserDataSerializer,
    OrderStatusSerializer,
    OrderItemStatusSerializer,
    OrderCommentSerializer,
    PublicOrderCheckoutSerializer,
    PublicOrderOwnerSerializer,
)

from .models import Order, OrderComment

from shops.models import Shop
from carts.views import get_users_cart, get_users_cart_items
from shared.exceptions import CustomException
from shared.services import send_mailgun_email, get_url
from shared.pagination import PaginationMixin, CustomPagination
from products.serializers import PublicProductSerializer
from blacklists.models import Blacklist
from customers.models import Customer
from users.models import User


class OrderView(APIView, PaginationMixin):
    permission_classes = [AllowAny]
    pagination_class = CustomPagination
    serializer_class = OrderSerializer

    def get_geo_location(self, ip_address):
        request = requests.get(
            'https://ipgeolocation.abstractapi.com/v1/?api_key'
            '=ec4afaec214d4ab295cbd07430d136f8&ip_address=' + ip_address
        )

        response = request.json()
        return response

    def get_software_info(self, user_agent):
        return SoftwareDetector(user_agent).parse()

    def check_order_expiration(self, order):
        if order.current_status == 0 and order.expires_at < timezone.now():
            instance = OrderStatusSerializer()
            OrderStatusSerializer.create(instance, {'order': order, 'status': -1})

            for order_item in order.items.all():
                item_instance = OrderItemStatusSerializer()
                OrderItemStatusSerializer.create(item_instance, {'item': order_item, 'status': -1})

    def send_order_email(self, order):
        if not order.email_sent:
            order_link = os.environ['SITE_SCHEME'] + os.environ['SITE_URL'] + '/checkout/' + str(order.shop.ref_id) + \
                         '/' + str(order.ref_id)

            order_values = []
            for order_item in order.items.all():
                order_item_data = PublicProductSerializer(order_item.product).data
                order_values.append(order_item_data)

            context = {
                'order_id': order.ref_id,
                'order_link': order_link,
                'order_items': order_values,
                'shop_name': order.shop.name
            }

            email_subject = order.shop.name + ' Order Created'
            email_body = render_to_string(
                os.path.join(settings.BASE_DIR, 'templates', 'emails', 'new_order.jinja2'),
                context
            )

            send_mailgun_email(order.email, email_subject, email_body, 'order')

    def check_seach_query(self, shop_ref, query):
        order = Order.objects.filter(shop_id__ref_id=shop_ref, email__contains=query).order_by('-created_at')

        if not order:
            data = {
                'success': False,
                'message': 'Order(s) that match your criteria were not found.',
                'data': {
                    'results': []
                },
            }

            return Response(data, status=status.HTTP_200_OK)

        return order

    def check_blacklist(self, shop_ref, user_ref, geo_data):
        return Blacklist.objects.filter(
            Q(shop_id__ref_id=shop_ref), Q(user__ref_id=user_ref) |
            Q(ip_address=geo_data['ip_address']) | Q(country=geo_data['country'])
        ).exists()

    def create_customer(self, email, shop):
        try:
            customer = Customer.objects.get(user__email=email, shop=shop)
            customer.user.last_login = timezone.now()
            customer.user.save()
        except Customer.DoesNotExist:
            user = User.objects.create(email=email)
            customer = Customer.objects.create(user=user, shop=shop)

        return customer

    def get(self, request, order_ref=None, shop_ref=None):
        orders = None

        if order_ref is not None:
            try:
                order = Order.objects.get(ref_id=order_ref)
                self.check_order_expiration(order)

                if 'checkout' in request.path:
                    orders = PublicOrderCheckoutSerializer(order).data
                else:
                    orders = PublicOrderOwnerSerializer(order).data
            except Order.DoesNotExist:
                raise CustomException(
                    'An order with order id ' + str(order_ref) + ' was not found.',
                    status.HTTP_404_NOT_FOUND,
                )

        elif shop_ref is not None:
            seach_query = request.query_params.get('q')
            if seach_query:
                order = self.check_seach_query(shop_ref, seach_query)
            else:
                order = Order.objects.filter(shop_id__ref_id=shop_ref).exclude(email=None).order_by('-created_at')

            if not order:
                raise CustomException(
                    'Orders from shop with id ' + str(shop_ref) + ' were not found.',
                    status.HTTP_204_NO_CONTENT,
                )

            for single_order in order:
                self.check_order_expiration(single_order)

            page = self.paginate_queryset(order)

            if page is not None:
                orders_data = PublicOrderOwnerSerializer(page, many=True).data
                orders = self.get_paginated_response(orders_data).data
            else:
                orders = PublicOrderOwnerSerializer(order, many=True).data

        data = {
            'success': True,
            'message': 'Order(s) that match your criteria were found.',
            'data': orders,
        }

        return Response(data, status=status.HTTP_200_OK)

    def post(self, request):
        order_data = request.data

        user_cookie = request.COOKIES.get('_enfront_uid')
        cart_cookie = request.COOKIES.get('_enfront_cid')
        cart = get_users_cart(cart_cookie)

        if cart is None:
            raise CustomException(
                'Cart with ID ' + str(cart_cookie) + ' could not be found.',
                status.HTTP_404_NOT_FOUND
            )

        cart_items = get_users_cart_items(cart)

        # check if item quantities are in the specified bounds
        for item in cart_items:
            if item['quantity'] < item['min_order_quantity'] or item['quantity'] > item['max_order_quantity']:
                raise CustomException(
                    'Quantity must be between ' + item['min_order_quantity'] + ' and ' + item['max_order_quantity'],
                    status.HTTP_400_BAD_REQUEST
                )

        context = {
            'request': request,
            'user_ref': user_cookie,
            'cart_items': cart_items,
            'cart': cart,
            'shop_ref': order_data.get('shop')
        }

        serialized_data = self.serializer_class(data=order_data, context=context)
        is_valid = serialized_data.is_valid(raise_exception=True)

        if not is_valid:
            raise CustomException(
                'There was a problem creating an order.',
                status.HTTP_400_BAD_REQUEST
            )

        client_ip = get_client_ip(request)
        geo_data = self.get_geo_location(client_ip[0])
        device_data = self.get_software_info(request.META['HTTP_USER_AGENT'])
        blacklist = self.check_blacklist(order_data['shop'], user_cookie, geo_data)

        if blacklist:
            return HttpResponseRedirect(get_url('/404'))

        order = serialized_data.create(serialized_data.data)

        user_data = {
            'order': order.id,
            'ip_address': geo_data['ip_address'],
            'using_vpn': geo_data['security']['is_vpn'],
            'longitude': geo_data['longitude'],
            'latitude': geo_data['latitude'],
            'city': geo_data['city'],
            'region': geo_data['region'],
            'postal_code': geo_data['postal_code'],
            'country': geo_data['country'],
            'browser': device_data.client_name(),
            'os': device_data.os_name()
        }

        serialized_data = OrderUserDataSerializer(data=user_data, context=context)
        is_valid = serialized_data.is_valid(raise_exception=True)

        if not is_valid:
            raise CustomException(
                'There was a problem saving the user.',
                status.HTTP_400_BAD_REQUEST
            )

        serialized_data.create(serialized_data.data)

        return HttpResponseRedirect(get_url('/checkout/' + str(order_data['shop']) + '/' + str(order.ref_id)))

    def patch(self, request, order_ref):
        order_data = request.data
        user_cookie = request.COOKIES.get('_enfront_uid')

        if order_data.get('email') is None:
            raise CustomException(
                'Email is required.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        elif order_ref is None:
            raise CustomException(
                'Order ref ID is required.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        context = {'request': request, 'user_ref': user_cookie}
        serialized_data = self.serializer_class(data=order_data, context=context, partial=True)
        is_valid = serialized_data.is_valid(raise_exception=True)

        if not is_valid:
            raise CustomException(
                'There was a problem updating this order.',
                status.HTTP_400_BAD_REQUEST
            )

        try:
            order_to_update = Order.objects.get(ref_id=order_ref)
            self.send_order_email(order_to_update)

            customer = self.create_customer(order_data.get('email'), order_to_update.shop)
            order = serialized_data.partial_update(order_to_update, serialized_data.data, customer)
        except Order.DoesNotExist:
            raise CustomException(
                'An order with id ' + str(order_ref) + ' was not found.',
                status.HTTP_404_NOT_FOUND,
            )

        data = {
            'success': True,
            'message': 'Order ' + str(order_ref) + ' has been updated.',
            'data': {
                'ref_id': order.ref_id,
                'email': order.email,
            },
        }

        return Response(data, status=status.HTTP_200_OK)


class OrderCommentView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderCommentSerializer

    def post(self, request):
        comment_data = request.data

        if comment_data.get('comment') is None:
            raise CustomException(
                'Comment text is required.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        elif comment_data.get('order') is None:
            raise CustomException(
                'Order ID must be in the query URL.',
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        context = {'request': request}
        serialized_data = self.serializer_class(data=comment_data, context=context)
        is_valid = serialized_data.is_valid(raise_exception=True)

        if not is_valid:
            raise CustomException(
                'There was a problem creating a comment.',
                status.HTTP_400_BAD_REQUEST
            )

        comment = serialized_data.create(serialized_data.data)

        data = {
            'success': True,
            'message': 'A comment has been created.',
            'data': {
                'comment': comment.comment,
                'created_at': comment.created_at,
                'ref_id': comment.ref_id
            }
        }

        return Response(data, status=status.HTTP_201_CREATED)

    def delete(self, request, comment_ref):
        if comment_ref is None:
            raise CustomException(
                'A comment id must be provided',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        try:
            comment = OrderComment.objects.get(ref_id=comment_ref)
            comment.status = -1
            comment.save()
        except OrderComment.DoesNotExist:
            raise CustomException(
                'A comment with pk ' + str(comment_ref) + ' was not found.',
                status.HTTP_404_NOT_FOUND,
            )

        data = {
            'success': True,
            'message': "A comment with id " + str(comment_ref) + " was deleted.",
            "data": {},
        }

        return Response(data, status=status.HTTP_204_NO_CONTENT)


class OrderStatView(APIView):
    permission_classes = [IsAuthenticated]

    def daterange(self, start_date, end_date):
        for n in range(int((end_date - start_date).days)):
            yield start_date + timedelta(n)

    def get_all_orders(self, shop):
        all_orders = Order.objects.filter(shop=shop, current_status__gte=1)

        return all_orders

    def get_all_orders_profit(self, all_orders):
        total_profit = 0
        for order in all_orders:
            total_profit += order.total

        return total_profit

    def get_past_orders(self, shop):
        past_orders = Order.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=7),
            shop=shop,
            current_status__gte=1
        ).values(
            'created_at'
        ).annotate(
            days=ExtractDay('created_at'),
        )

        stats = [0] * 7
        for order in past_orders:
            for idx, date in enumerate(self.daterange(timezone.now() - timedelta(days=7), timezone.now())):
                if order['created_at'].day == date.day + 1:
                    stats[idx] += 1

        return stats

    def get_past_orders_profit(self, shop):
        past_orders = Order.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=7),
            shop=shop,
            current_status__gte=1
        )

        past_profit = decimal.Decimal('0.0')
        if past_orders.count() > 0:
            for past_order in past_orders:
                past_profit += past_order.total

        return past_profit

    def get(self, request, shop_ref):
        if shop_ref is None:
            raise CustomException(
                'Shop ID is required.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        shop = Shop.objects.get(ref_id=shop_ref)
        all_orders = self.get_all_orders(shop)
        all_orders_count = all_orders.count()
        all_orders_profit = self.get_all_orders_profit(all_orders)

        past_orders = self.get_past_orders(shop)
        past_orders_profit = self.get_past_orders_profit(shop)

        data = {
            'success': True,
            'message': 'Orders have been been found.',
            "data": {
                'all_orders': all_orders_count,
                'past_orders': past_orders,
                'total_profit': all_orders_profit,
                'past_profit': past_orders_profit,
            },
        }

        return Response(data, status=status.HTTP_200_OK)
