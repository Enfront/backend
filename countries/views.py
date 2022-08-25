from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status

from .models import Country
from .serializers import PublicCountrySerializer


class CountryView(APIView):
    def get(self, request):
        all_countries = Country.objects.all()
        serialized_data = PublicCountrySerializer(all_countries, many=True).data

        data = {
            'success': True,
            'message': 'A list of countries was found.',
            'data': serialized_data,
        }

        return Response(data, status=status.HTTP_200_OK)
