from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Shop
from .serializers import ShopSerializer, PublicShopSerializer

from shared.exceptions import CustomException
from shared.services import get_subscription


class ShopView(APIView):
    def check_existing_domain(self, domain, shop_ref=None):
        if shop_ref is not None:
            return Shop.objects.filter(domain=domain).exclude(status=-1).exclude(ref_id=shop_ref).exists()

        return Shop.objects.filter(domain=domain).exclude(status=-1).exists()

    def check_subscription_limits(self, user, is_edit):
        subscription = get_subscription(user_pk=user)

        if is_edit:
            shop_count = Shop.objects.filter(owner=user, status=1).count()
        else:
            shop_count = Shop.objects.filter(owner=user).exclude(status=-1).count()

        if shop_count >= subscription['max_shops']:
            raise CustomException(
                'You have reached the maximum number of shops for your subscription tier.',
                status.HTTP_401_UNAUTHORIZED,
            )

    def get(self, request, ref_id=None):
        if ref_id is not None:
            try:
                shop = Shop.objects.exclude(status=-1).get(owner=request.user, ref_id=ref_id)
                shop_data = PublicShopSerializer(shop).data
            except Shop.DoesNotExist:
                raise CustomException(
                    'A shop with id ' + str(ref_id) + ' does not exist.',
                    status.HTTP_404_NOT_FOUND,
                )
        else:
            shop = Shop.objects.filter(owner=request.user).exclude(status=-1)
            shop_data = PublicShopSerializer(shop, many=True).data

            if not shop:
                raise CustomException(
                    'No shops were found for this user.',
                    status.HTTP_204_NO_CONTENT,
                )

        data = {
            'success': True,
            'message': 'Shop(s) that match your criteria were found.',
            'data': shop_data,
        }

        return Response(data, status=status.HTTP_200_OK)

    def post(self, request):
        shop_data = request.data

        if shop_data.get('email') is None:
            raise CustomException(
                'A shop email is required.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        elif shop_data.get('name') is None:
            raise CustomException(
                'A shop name is required.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        elif shop_data.get('domain') is None:
            raise CustomException(
                'A domain is required.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        elif shop_data.get('country') is None:
            raise CustomException(
                'A country is required.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        if self.check_existing_domain(shop_data['domain']):
            raise CustomException(
                'A shop with this domain already exists.',
                status.HTTP_409_CONFLICT
            )

        context = {'request': request, 'country': shop_data['country']}
        serialized_data = ShopSerializer(data=shop_data, context=context)
        is_valid = serialized_data.is_valid()

        if not is_valid:
            data = {
                'success': False,
                'message': 'Shop data is invalid.',
                'data': {}
            }

            return Response(data, status=status.HTTP_400_BAD_REQUEST)

        self.check_subscription_limits(request.user.pk, False)

        shop = serialized_data.create(serialized_data.data, owner_id=request.user.pk)
        if not shop:
            raise CustomException(
                'There was a problem creating a shop.',
                status.HTTP_400_BAD_REQUEST
            )

        data = {
            'success': True,
            'message': shop.name + ' has been created.',
            'data': {
                'ref_id': shop.ref_id,
                'name': shop.name,
                'domain': shop.domain,
            },
        }

        return Response(data, status=status.HTTP_201_CREATED)

    def put(self, request, ref_id=None):
        shop_data = request.data

        if ref_id is None:
            raise CustomException(
                'A shop ref must be provided.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        elif shop_data.get('status') is None:
            raise CustomException(
                'A status must be provided.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        elif shop_data.get('domain') is None:
            raise CustomException(
                'A domain must be provided.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        try:
            shop = Shop.objects.get(owner=request.user, ref_id=ref_id)
        except Shop.DoesNotExist:
            raise CustomException(
                'A shop with the ref id ' + str(ref_id) + ' could not be found.',
                status.HTTP_404_NOT_FOUND,
            )

        if self.check_existing_domain(shop_data['domain'], ref_id):
            raise CustomException(
                'A shop with with this domain already exists.',
                status.HTTP_409_CONFLICT,
            )

        if int(shop_data['status']) == 1 and int(shop_data['status']) != shop.status:
            self.check_subscription_limits(shop.owner.pk, True)

        if shop_data.get('name') is not None:
            shop.name = shop_data['name']

        if shop_data.get('email') is not None:
            shop.email = shop_data['email']

        shop.status = shop_data['status']
        shop.domain = shop_data['domain']
        shop.save()

        data = {
            'success': True,
            'message': 'Shop ' + str(ref_id) + ' has been updated.',
            'data': {},
        }

        return Response(data, status=status.HTTP_200_OK)

    def delete(self, request, ref_id=None):
        if ref_id is None:
            raise CustomException(
                'A shop ref must be provided.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        try:
            shop = Shop.objects.get(owner=request.user, ref_id=ref_id)
            shop.status = -1
            shop.save()
        except Shop.DoesNotExist:
            raise CustomException(
                'There was an error deleting shop with id ' + str(ref_id) + '.',
                status.HTTP_400_BAD_REQUEST
            )

        data = {
            'success': True,
            'message': 'A shop with ref id ' + str(ref_id) + ' was deleted.',
            'data': {},
        }

        return Response(data, status=status.HTTP_204_NO_CONTENT)
