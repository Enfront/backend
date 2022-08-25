from django.utils import timezone
from rest_framework import serializers, status

import decimal

from uuid import UUID, uuid4
from itertools import chain

from .models import Order, OrderItem, OrderStatus, OrderItemStatus, OrderUserData, OrderComment

from products.models import Product, DigitalProduct
from products.serializers import PublicProductSerializer, PublicDigitalProductSerializer
from shops.models import Shop
from shops.serializers import PublicShopOrderSerializer
from users.models import User
from users.serializers import PublicUserInfoSerializer
from shared.exceptions import CustomException
from carts.views import delete_cart_item
from customers.models import Customer
from payments.models import Payment


class OrderItemSerializer(serializers.ModelSerializer):
    product = serializers.SerializerMethodField()

    def get_product(self, product_ref):
        return Product.objects.get(ref_id=product_ref)

    def check_item_stock(self, buy_quantity, sell_quantity):
        if buy_quantity > sell_quantity:
            return False

        return True

    def create(self, order, **kwargs):
        for cart_item in kwargs.get('cart_items'):
            is_available = self.check_item_stock(cart_item['quantity'], cart_item['stock'])
            
            order_item = OrderItem.objects.create(
                order=order,
                quantity=cart_item['quantity'],
                product=self.get_product(cart_item['ref_id']),
                price=cart_item['price'],
                current_status=(-2 if not is_available else 0)
            )

            order.items.add(order_item)
            delete_cart_item(kwargs.get('cart').id, cart_item['ref_id'])

        instance = OrderStatusSerializer()
        OrderStatusSerializer.create(instance, {'order': order, 'status': 0})

        return kwargs.get('cart_items')

    class Meta:
        model = OrderItem
        fields = '__all__'


class OrderSerializer(serializers.ModelSerializer):
    total = serializers.SerializerMethodField()

    def get_total(self, _):
        if self.context.get('cart_items'):
            total = decimal.Decimal(0.00)
            for item in self.context['cart_items']:
                total += item['price'] * item['quantity']

            return total

        return decimal.Decimal(0.00)

    def get_shop(self):
        try:
            return Shop.objects.get(ref_id=self.context['shop_ref'])
        except Shop.DoesNotExist:
            raise CustomException(
                'Shop with id ' + str(self.context['shop_id']) + ' does not exist.',
                status.HTTP_404_NOT_FOUND,
            )

    def create(self, validated_data):
        validated_data['shop'] = self.get_shop()
        order = Order.objects.create(**validated_data)

        instance = OrderItemSerializer()
        OrderItemSerializer.create(instance, order, cart=self.context['cart'], cart_items=self.context['cart_items'])

        return order

    def partial_update(self, instance, validated_data, customer):
        instance.email = validated_data['email']
        instance.customer = customer
        instance.email_sent = True
        instance.save()

        return instance

    class Meta:
        model = Order
        fields = ['email', 'customer', 'total', 'ref_id', 'expires_at', 'current_status']


class OrderStatusSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        order_status = OrderStatus.objects.create(**validated_data)

        current_order_status = Order.objects.get(id=validated_data.get('order').id)
        current_order_status.current_status = validated_data.get('status')
        current_order_status.save()

        return order_status

    class Meta:
        model = OrderStatus
        fields = '__all__'


class OrderItemStatusSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        order_item_status = OrderItemStatus.objects.create(**validated_data)

        current_order_item_status = OrderItem.objects.get(id=validated_data.get('item').id)
        current_order_item_status.current_status = validated_data.get('status')
        current_order_item_status.save()

        return order_item_status

    class Meta:
        model = OrderItemStatus
        fields = '__all__'


class OrderUserDataSerializer(serializers.ModelSerializer):
    def get_order(self, order_id):
        return Order.objects.get(id=order_id)

    def create(self, validated_data):
        validated_data['order'] = self.get_order(validated_data.get('order'))
        user_data = OrderUserData.objects.create(**validated_data)

        return user_data

    class Meta:
        model = OrderUserData
        fields = '__all__'


class OrderCommentSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    order = serializers.UUIDField()

    def get_user(self, request):
        try:

            if isinstance(request, OrderComment):
                user_id = request.user.pk
                commenter = User.objects.get(pk=user_id)
                commenter = PublicUserInfoSerializer(commenter).data
            else:
                user_id = self.context['request'].user.pk
                commenter = User.objects.get(pk=user_id)

            return commenter
        except User.DoesNotExist:
            return None

    def get_order(self, order):
        return Order.objects.get(ref_id=order)

    def create(self, validated_data):
        validated_data['order'] = self.get_order(validated_data.get('order'))
        order = OrderComment.objects.create(**validated_data)

        return order

    class Meta:
        model = OrderComment
        fields = '__all__'


class PublicOrderCommentSerializer(OrderCommentSerializer):
    class Meta:
        model = OrderComment
        fields = ['comment', 'user', 'ref_id', 'created_at']


class PublicOrderUserDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderUserData
        fields = ['ip_address', 'using_vpn', 'longitude', 'latitude', 'city', 'region', 'postal_code', 'country',
                  'browser', 'os']


class PublicOrderStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatus
        fields = ['status', 'created_at']


class PublicOrderItemStatusSerializer(serializers.ModelSerializer):
    item = serializers.SerializerMethodField()

    def get_item(self, request):
        item = OrderItem.objects.get(id=request.item_id)
        product = Product.objects.get(id=item.product_id)
        product_data = PublicProductSerializer(instance=product).data

        key = DigitalProduct.objects.filter(orderitem=item.id)
        product_data['key'] = PublicDigitalProductSerializer(key, many=True).data

        return product_data

    class Meta:
        model = OrderItemStatus
        fields = ['status', 'created_at', 'item']


class PublicOrderCheckoutSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    shop = PublicShopOrderSerializer()

    def get_items(self, request):
        order_items = []
        for item in request.items.all():
            items = PublicProductSerializer(item.product).data
            items['quantity'] = item.quantity
            items['current_status'] = item.current_status

            order_items.append(items)

        return order_items

    class Meta:
        model = Order
        fields = ['email', 'currency', 'current_status', 'total', 'shop', 'items', 'ref_id', 'created_at']


class PublicOrderOwnerSerializer(PublicOrderCheckoutSerializer):
    customer = serializers.SerializerMethodField()
    geo_data = serializers.SerializerMethodField()
    statuses = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()
    paypal_email = serializers.SerializerMethodField()

    def get_customer(self, request):
        try:
            customer_data = PublicOrderCustomerSerializer(request.customer).data
        except Customer.DoesNotExist:
            customer_data = None

        return customer_data

    def get_geo_data(self, request):
        try:
            geo_data = OrderUserData.objects.get(order__id=request.id)
            serialized_geo_data = PublicOrderUserDataSerializer(geo_data).data
        except OrderUserData.DoesNotExist:
            return None

        return serialized_geo_data

    def get_statuses(self, request):
        order_status = OrderStatus.objects.filter(order__ref_id=request.ref_id)
        order_status = PublicOrderStatusSerializer(order_status, many=True).data

        item_statuses = OrderItemStatus.objects.filter(item_id__order__ref_id=request.ref_id)
        item_statuses = PublicOrderItemStatusSerializer(item_statuses, many=True).data

        comments = OrderComment.objects.filter(order__ref_id=request.ref_id).exclude(status=-1)
        comments = PublicOrderCommentSerializer(comments, many=True).data

        combined_statuses = list(chain(order_status, item_statuses, comments))
        combined_statuses.sort(key=lambda x: x['created_at'], reverse=True)

        return combined_statuses

    def get_items(self, request):
        order_items = []
        for item in request.items.all():
            items = PublicProductSerializer(item.product).data
            items['quantity'] = item.quantity
            items['current_status'] = item.current_status

            order_items.append(items)

        return order_items

    def get_paypal_email(self, request):
        try:
            payment = Payment.objects.get(order_id=request.id, status=1)
        except Payment.DoesNotExist:
            return None

        if payment.provider != 0:
            return None

        return payment.provider_data['payer']['email_address']

    class Meta:
        model = Order
        fields = ['email', 'customer', 'paypal_email', 'geo_data', 'currency', 'total', 'shop', 'items', 'statuses',
                  'current_status', 'ref_id', 'created_at', 'updated_at']


class PublicOrderCustomerSerializer(serializers.ModelSerializer):
    completed_order_count = serializers.SerializerMethodField()
    user = PublicUserInfoSerializer()

    def get_completed_order_count(self, customer):
        try:
            orders = Order.objects.filter(customer=customer, current_status__gte=3)

            return orders.count()
        except Customer.DoesNotExist:
            return 0

    class Meta:
        model = Customer
        fields = ['user', 'completed_order_count']
