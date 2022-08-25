from rest_framework import serializers
from rest_framework import status

import decimal

from .models import Customer, CustomerNote

from orders.models import Order
from orders.serializers import PublicOrderCheckoutSerializer
from shops.models import Shop
from users.models import User
from users.serializers import PublicUserInfoSerializer
from shared.pagination import PaginationMixin
from shared.exceptions import CustomException


class CustomerSerializer(serializers.ModelSerializer):
    customer = serializers.UUIDField()

    def get_customer(self, validated_data):
        try:
            customer = Customer.objects.get(ref_id=validated_data['customer'])
            return customer
        except Customer.DoesNotExist:
            raise CustomException(
                'A customer with the ref id ' + str(validated_data['customer']) + ' does not exist.',
                status.HTTP_404_NOT_FOUND
            )

    class Meta:
        model = Customer
        fields = '__all__'


class CustomerNoteSerializer(serializers.ModelSerializer):
    customer = serializers.UUIDField()
    user = serializers.SerializerMethodField()

    def get_customer(self, validated_data):
        try:
            customer = Customer.objects.get(user__ref_id=validated_data['customer'])
            return customer
        except Customer.DoesNotExist:
            raise CustomException(
                'A customer with the ref id ' + str(validated_data['customer']) + ' does not exist.',
                status.HTTP_404_NOT_FOUND
            )

    def get_user(self, _):
        try:
            user = User.objects.get(pk=self.context.get('request').user.pk)
            return user
        except User.DoesNotExist:
            raise CustomException(
                'A user with the ref id ' + str(validated_data['customer']) + ' does not exist.',
                status.HTTP_404_NOT_FOUND
            )

    def create(self, validated_data):
        if not validated_data['note']:
            raise CustomException(
                'A note must be included in the request.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        elif not validated_data['customer']:
            raise CustomException(
                'A customer ref id must be included in the request.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        validated_data['customer'] = self.get_customer(validated_data)
        validated_data['user'] = self.get_user(validated_data)
        note = CustomerNote.objects.create(**validated_data)

        return note

    class Meta:
        model = CustomerNote
        fields = '__all__'


class PublicCustomerInfoSerializer(serializers.ModelSerializer):
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


class PublicCustomerExpandedSerializer(PublicCustomerInfoSerializer, PaginationMixin):
    all_order_count = serializers.SerializerMethodField()
    total_spent = serializers.SerializerMethodField()
    orders = serializers.SerializerMethodField()
    user = PublicUserInfoSerializer()

    def get_all_order_count(self, customer):
        try:
            orders = Order.objects.filter(customer=customer)

            return orders.count()
        except Customer.DoesNotExist:
            return 0

    def get_total_spent(self, customer):
        try:
            orders = Order.objects.filter(customer=customer)

            total_spent = decimal.Decimal(0.00)
            for order in orders:
                if order.current_status == 3:
                    total_spent += decimal.Decimal(order.total)

            return total_spent
        except Customer.DoesNotExist:
            return 0

    def get_orders(self, customer):
        try:
            orders = Order.objects.filter(customer=customer)
            orders_data = PublicOrderCheckoutSerializer(orders, many=True).data

            return orders_data
        except Customer.DoesNotExist:
            return []

    class Meta:
        model = Customer
        fields = ['completed_order_count', 'all_order_count', 'total_spent', 'orders', 'user']


class PublicCustomerNoteSerializer(serializers.ModelSerializer):
    user = PublicUserInfoSerializer()

    class Meta:
        model = CustomerNote
        fields = ['note', 'user', 'created_at', 'ref_id']
