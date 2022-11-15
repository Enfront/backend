from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Blacklist
from .serializers import PublicBlacklistSerializer, BlacklistSerializer

from shared.exceptions import CustomException
from shared.pagination import PaginationMixin, CustomPagination


class BlacklistView(APIView, PaginationMixin):
    pagination_class = CustomPagination
    serializer_class = BlacklistSerializer

    def get(self, request, shop_ref):
        if shop_ref is None:
            raise CustomException(
                'Shop ref id is required.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        blacklist = Blacklist.objects.filter(shop__owner=request.user, shop_id__ref_id=shop_ref)
        if not blacklist.exists():
            data = {
                'success': True,
                'message': 'Blacklist item(s) that match your criteria could not be found.',
                'data': {}
            }

            return Response(data, status=status.HTTP_204_NO_CONTENT)

        page = self.paginate_queryset(blacklist)
        if page is not None:
            blacklist_data = PublicBlacklistSerializer(page, many=True).data
            blacklist_paginated = self.get_paginated_response(blacklist_data).data
        else:
            blacklist_paginated = PublicBlacklistSerializer(blacklist, many=True).data

        data = {
            'success': True,
            'message': 'Blacklist item(s) that match your criteria were found.',
            'data': blacklist_paginated
        }

        return Response(data, status=status.HTTP_200_OK)

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

    def delete(self, request, ref_id):
        if ref_id is None:
            raise CustomException(
                'A blacklist ref must be provided.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        try:
            blacklist = Blacklist.objects.get(shop__owner=request.user, ref_id=ref_id)
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
