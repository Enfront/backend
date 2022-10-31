from rest_framework import serializers
from rest_framework import status

from .models import Payout

from shared.exceptions import CustomException
from shops.models import Shop


class PayoutSerializer(serializers.ModelSerializer):
    shop = serializers.UUIDField()

    def get_shop(self, ref_id):
        try:
            return Shop.objects.get(ref_id=ref_id)
        except Shop.DoesNotExist:
            raise CustomException(
                'A shop with id ' + str(ref_id) + ' was not found.',
                status.HTTP_404_NOT_FOUND
            )

    def create(self, validated_data):
        validated_data['shop'] = self.get_shop(validated_data.get('shop'))
        return Payout.objects.create(**validated_data)

    class Meta:
        model = Payout
        fields = '__all__'


class PublicPayoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payout
        fields = ['amount', 'created_at', 'currency', 'destination', 'ref_id', 'status', 'updated_at']
