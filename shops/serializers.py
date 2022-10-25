from django.utils.text import slugify
from rest_framework import serializers
from rest_framework import status

from uuid import uuid4
import os

from .models import Shop

from countries.models import Country
from countries.serializers import PublicCountrySerializer
from shared.exceptions import CustomException
from themes.models import Theme, ThemeConfiguration
from themes.serializers import PublicThemeSerializer


class ShopSerializer(serializers.ModelSerializer):
    country = serializers.SerializerMethodField()

    def get_country(self, request):
        return Country.objects.get(id=self.context['country'])

    def create(self, validated_data, **kwargs):
        if not kwargs.get('owner_id'):
            raise CustomException(
                'Owner id must be included in the request.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        owner_id = kwargs.get('owner_id')
        validated_data['domain'] = slugify(validated_data['name']) + '.' + os.environ['SITE_URL']

        shop = Shop.objects.create(owner_id=owner_id, **validated_data)

        theme = Theme.objects.get(id=1)
        ThemeConfiguration.objects.create(theme=theme, shop=shop, file_name=str(uuid4()) + '.json', status=1)

        return shop

    class Meta:
        model = Shop
        fields = '__all__'


class PublicShopSerializer(serializers.ModelSerializer):
    current_theme = serializers.SerializerMethodField()
    owner = serializers.SerializerMethodField()
    country = PublicCountrySerializer()

    def get_current_theme(self, request):
        theme_configuration = ThemeConfiguration.objects.get(shop_id=request, status=1)
        theme = Theme.objects.get(id=theme_configuration.theme_id)

        return PublicThemeSerializer(theme).data

    def get_owner(self, request):
        return {
            'username': request.owner.username,
            'subscription_tier': request.owner.subscription_tier
        }

    class Meta:
        model = Shop
        fields = ['name', 'email', 'status', 'currency', 'domain', 'country', 'current_theme', 'owner', 'ref_id']


class PublicShopOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ['name', 'domain', 'ref_id']
