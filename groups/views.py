from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Collection
from .serializers import CollectionSerializer, PublicCollectionSerializer

from shared.exceptions import CustomException


class CollectionView(APIView):
    serializer_class = CollectionSerializer

    def check_slug(self, slug, shop_ref):
        collection = Collection.objects.filter(shop__ref_id=shop_ref, slug=slug)

        if collection.exists():
            raise CustomException(
                'A collection with this slug already exists.',
                status.HTTP_409_CONFLICT
            )

    def get(self, request):
        collection = Collection.objects.filter(shop__owner=request.user).order_by('title')

        if collection.exists():
            collection_data = PublicCollectionSerializer(collection, many=True).data

            data = {
                'success': True,
                'message': 'Collection(s) that match your criteria were found.',
                'data': collection_data
            }

            return Response(data, status=status.HTTP_200_OK)

        data = {
            'success': False,
            'message': 'No collection(s) that match your criteria were found.',
            'data': None
        }

        return Response(data, status=status.HTTP_204_NO_CONTENT)

    def post(self, request):
        collection_data = request.data
        context = {'request': request}

        self.check_slug(collection_data['slug'], collection_data['shop'])

        serialized_data = self.serializer_class(data=collection_data, context=context)
        is_valid = serialized_data.is_valid(raise_exception=False)

        if not is_valid:
            raise CustomException(
                'There was a problem creating a collection.',
                status.HTTP_400_BAD_REQUEST
            )

        collection_ref_id = serialized_data.create(serialized_data.data)

        data = {
            'success': True,
            'message': 'A collection was created.',
            'data': {
                'ref_id': collection_ref_id
            }
        }

        return Response(data, status=status.HTTP_201_CREATED)

    def patch(self, request, collection_ref):
        collection_data = request.data

        try:
            collection = Collection.objects.get(shop__owner=request.user, ref_id=collection_ref)
        except Collection.DoesNotExist:
            raise CustomException(
                'There was an issue finding a collection with id ' + str(collection_ref) + '.',
                status.HTTP_404_NOT_FOUND
            )

        if collection_data['slug'] != collection.slug:
            self.check_slug(collection_data['slug'], collection_data['shop'])

        serialized_data = self.serializer_class(data=collection_data, partial=True)
        is_valid = serialized_data.is_valid(raise_exception=True)

        if not is_valid:
            raise CustomException(
                'There was a problem saving the collections data.',
                status.HTTP_400_BAD_REQUEST
            )

        serialized_data.partial_update(collection, serialized_data.data)

        data = {
            'success': True,
            'message': 'The collection was successfully saved.',
            'data': {}
        }

        return Response(data, status=status.HTTP_200_OK)

    def delete(self, request, collection_ref):
        try:
            collection = Collection.objects.get(shop__owner=request.user, ref_id=collection_ref)
            collection.delete()
        except Collection.DoesNotExist:
            raise CustomException(
                'There was an error deleting the collection with id ' + str(collection_ref) + '.',
                status.HTTP_404_NOT_FOUND
            )

        data = {
            'success': True,
            'message': 'The collection with a ref id ' + str(collection_ref) + ' was deleted.',
            'data': {},
        }

        return Response(data, status=status.HTTP_204_NO_CONTENT)
