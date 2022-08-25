from rest_framework import serializers

from uuid import uuid4

from .models import Theme, ThemeConfiguration

from shops.models import Shop


class ThemeConfigurationSerializer(serializers.ModelSerializer):
    shop = serializers.UUIDField()
    theme = serializers.UUIDField()
    file_name = serializers.SerializerMethodField()

    def get_shop(self, shop_ref):
        return Shop.objects.get(ref_id=shop_ref)

    def get_theme(self, theme_ref):
        return Theme.objects.get(ref_id=theme_ref)

    def get_file_name(self, _):
        file_uuid = uuid4()
        file_name = str(file_uuid) + '.json'

        return file_name

    def create(self, validated_data, **kwargs):
        validated_data['shop'] = self.get_shop(validated_data.get('shop'))
        validated_data['theme'] = self.get_theme(validated_data.get('theme'))
        validated_data['config_status'] = kwargs.get('activate_config')

        theme_config = ThemeConfiguration.objects.create(**validated_data)

        return theme_config

    def partial_update(self, instance, validated_data, **kwargs):
        instance.config_status = kwargs.get('activate_config')
        instance.status = validated_data.get('status')
        instance.save()

        return instance

    class Meta:
        model = ThemeConfiguration
        fields = '__all__'


class PublicThemeSerializer(serializers.ModelSerializer):
    developer = serializers.SerializerMethodField()

    def get_developer(self, request):
        return request.developer.username

    class Meta:
        model = Theme
        fields = ['name', 'description', 'developer', 'updated_at', 'ref_id']
