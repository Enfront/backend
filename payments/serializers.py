from rest_framework import serializers, status

from collections import OrderedDict
from operator import itemgetter

from .models import Payment, PaymentSession, PaymentProvider

from orders.models import Order
from shared.exceptions import CustomException
from shared.services import get_order_fees


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

        if request['canceled_at'] is not None:
            return 0

        return get_order_fees(order.total, order.shop.ref_id, request['provider'])

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


class PublicPaymentProviderSerializer(serializers.ModelSerializer):
    paypal_email = serializers.SerializerMethodField()
    stripe_id = serializers.SerializerMethodField()
    bitcoin_address = serializers.SerializerMethodField()

    def get_paypal_email(self, request):
        if request.provider == 0:
            return request.provider_data['email']

    def get_stripe_id(self, request):
        if request.provider == 1:
            if not request.provider_data.get('details_submitted') and not request.provider_data.get('charges_enabled'):
                return None

            return request.provider_data['id']

    def get_bitcoin_address(self, request):
        if request.provider == 2:
            return request.provider_data['bitcoin_address']

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep = OrderedDict(filter(itemgetter(1), rep.items()))

        return rep

    class Meta:
        model = PaymentProvider
        fields = ['bitcoin_address', 'paypal_email', 'stripe_id']


class PublicCryptoAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentProvider
        fields = ['provider_data', 'balance']
