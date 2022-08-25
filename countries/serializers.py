from rest_framework import serializers

from .models import Country


class PublicCountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ['id', 'num_code', 'iso_2', 'iso_3', 'name', 'continent', 'stripe_available', 'paypal_available']
