from rest_framework import serializers
from rest_framework import status

from .models import Subscription, SubscriptionPayment

from users.models import User
from shared.services import get_total_fees
from shared.exceptions import CustomException
from orders.models import Order
from orders.serializers import PublicOrderCheckoutSerializer
from payments.models import Payment


class SubscriptionSerializer(serializers.ModelSerializer):
    def get_user(self, pk):
        try:
            return User.objects.get(pk=pk)
        except User.DoesNotExist:
            raise CustomException(
                'A user with id was not found.',
                status.HTTP_404_NOT_FOUND
            )

    def create(self, validated_data):
        validated_data['user'] = self.get_user(validated_data.get('user'))
        subscription = Subscription.objects.create(**validated_data)

        return subscription

    class Meta:
        model = Subscription
        fields = '__all__'


class SubscriptionPaymentSerializer(serializers.ModelSerializer):
    def get_user(self, pk):
        try:
            return User.objects.get(pk=pk)
        except User.DoesNotExist:
            raise CustomException(
                'A user with id was not found.',
                status.HTTP_404_NOT_FOUND
            )

    def create(self, validated_data):
        validated_data['user'] = self.get_user(validated_data.get('user'))
        subscription = SubscriptionPayment.objects.create(**validated_data)

        return subscription

    class Meta:
        model = SubscriptionPayment
        fields = '__all__'


class PublicSubscriptionSerializer(serializers.ModelSerializer):
    total_fees = serializers.SerializerMethodField()
    cancel_at_period_end = serializers.SerializerMethodField()
    current_period_end = serializers.SerializerMethodField()
    subscription_id = serializers.SerializerMethodField()

    def get_total_fees(self, _):
        return get_total_fees(self.context.get('shop_ref'))

    def get_cancel_at_period_end(self, request):
        return request.provider_data['cancel_at_period_end']

    def get_current_period_end(self, request):
        return request.provider_data['current_period_end']

    def get_subscription_id(self, request):
        return request.provider_data['id']

    class Meta:
        model = Subscription
        fields = ['total_fees', 'cancel_at_period_end', 'current_period_end', 'subscription_id', 'ref_id']
