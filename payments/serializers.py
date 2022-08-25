from django.utils import timezone
from rest_framework import serializers

from datetime import timedelta
import decimal
import math

from .models import Payment, PaymentSession, PaymentProvider

from orders.models import Order
from shared.services import get_subscription
from shared.exceptions import CustomException


class PaymentSerializer(serializers.ModelSerializer):
    fee = serializers.SerializerMethodField()

    def get_fee(self, request):
        try:
            order = Order.objects.get(ref_id=self.context['order'].ref_id)
        except Order.DoesNotExist:
            raise CustomException(
                'An order with id ' + str(self.context['order'].ref_id) + ' could not be found.',
                status.HTTP_404_NOT_FOUND
            )

        # Take 0% fees for PayPal
        if request['provider'] == 0:
            return decimal.Decimal(0.00)

        subscription = get_subscription(shop_ref=order.shop.ref_id)
        return math.ceil(order.total * subscription['fee'])

    def create(self, validated_data):
        validated_data['order'] = self.context['order']
        payment = Payment.objects.create(**validated_data)

        return payment

    class Meta:
        model = Payment
        fields = '__all__'


class PaymentSessionSerializer(serializers.ModelSerializer):
    def create(self, validated_data, **kwargs):
        validated_data['order'] = kwargs.get('order')
        session = PaymentSession.objects.create(**validated_data)

        return session

    class Meta:
        model = PaymentSession
        fields = '__all__'


class PaymentProviderSerializer(serializers.ModelSerializer):
    def create(self, validated_data, **kwargs):
        validated_data['shop'] = kwargs.get('shop')
        provider = PaymentProvider.objects.create(**validated_data)

        return provider

    class Meta:
        model = PaymentProvider
        fields = '__all__'
