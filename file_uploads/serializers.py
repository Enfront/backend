from rest_framework import serializers

from .models import FileData


class PublicImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileData
        fields = ['ref_id', 'path']