from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Blacklist
from .serializers import PublicBlacklistSerializer, BlacklistSerializer

from shared.exceptions import CustomException


class BlacklistView(APIView):
    serializer_class = BlacklistSerializer

    def post(self, request):
        blacklist_data = request.data
        context = {'request': request}

        serialized_data = self.serializer_class(data=blacklist_data, context=context)
        is_valid = serialized_data.is_valid(raise_exception=True)

        if not is_valid:
            raise CustomException(
                'There was a problem creating a blacklist item.',
                status.HTTP_400_BAD_REQUEST
            )

        blacklist_ref_id = serialized_data.create(serialized_data.data)

        data = {
            'success': True,
            'message': 'A blacklist item was created.',
            'data': {
                'ref_id': blacklist_ref_id
            }
        }

        return Response(data, status=status.HTTP_200_OK)

    def get(self, request, shop_ref):
        if shop_ref is None:
            raise CustomException(
                'Shop ref id is required.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        blacklist = Blacklist.objects.filter(shop_id__ref_id=shop_ref)
        blacklist_data = PublicBlacklistSerializer(blacklist, many=True).data

        data = {
            'success': True,
            'message': 'Blacklist item(s) that match your criteria were found.',
            'data': blacklist_data
        }

        return Response(data, status=status.HTTP_200_OK)

    def delete(self, request, ref_id):
        if ref_id is None:
            raise CustomException(
                'A blacklist ref must be provided.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        try:
            blacklist = Blacklist.objects.get(ref_id=ref_id)
            blacklist.delete()
        except Blacklist.DoesNotExist:
            raise CustomException(
                'There was an error deleting a blacklist item with id ' + str(ref_id) + '.',
                status.HTTP_400_BAD_REQUEST
            )

        data = {
            'success': True,
            'message': 'A blacklist item with a ref id ' + str(ref_id) + ' was deleted.',
            'data': {},
        }

        return Response(data, status=status.HTTP_204_NO_CONTENT)
