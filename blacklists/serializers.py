from rest_framework import serializers, status

from .models import Blacklist

from shops.models import Shop
from users.models import User
from shared.exceptions import CustomException


class BlacklistSerializer(serializers.ModelSerializer):
    shop = serializers.UUIDField()
    user = serializers.UUIDField(required=False)

    def get_shop(self, ref_id):
        try:
            return Shop.objects.get(ref_id=ref_id)
        except Shop.DoesNotExist:
            raise CustomException(
                'A shop with id ' + str(ref_id) + ' was not found.',
                status.HTTP_404_NOT_FOUND
            )

    def get_user(self, ref_id):
        try:
            return User.objects.get(ref_id=ref_id)
        except User.DoesNotExist:
            raise CustomException(
                'A user with id ' + str(ref_id) + ' was not found.',
                status.HTTP_404_NOT_FOUND
            )

    def create(self, validated_data, **kwargs):
        shop = self.get_shop(validated_data['shop'])

        if validated_data['ip_address'] is not None:
            blacklist_item = Blacklist.objects.create(ip_address=validated_data['ip_address'], shop=shop)
        elif validated_data['country'] is not None:
            blacklist_item = Blacklist.objects.create(country=validated_data['country'], shop=shop)
        elif validated_data['paypal_email'] is not None:
            blacklist_item = Blacklist.objects.create(paypal_email=validated_data['paypal_email'], shop=shop)
        else:
            user = self.get_user(validated_data['user'])
            blacklist_item = Blacklist.objects.create(user=user, shop=shop)

        return blacklist_item.ref_id

    class Meta:
        model = Blacklist
        fields = '__all__'


class PublicBlacklistSerializer(serializers.ModelSerializer):
    email = serializers.SerializerMethodField()

    def get_email(self, item):
        if item.user:
            return item.user.email

        return None

    class Meta:
        model = Blacklist
        fields = ['email', 'ip_address', 'paypal_email', 'country', 'ref_id']
