from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from detect_delimiter import detect
from uuid import uuid4

import os
import boto3

from .models import Product, DigitalProduct
from .serializers import ProductSerializer, PublicProductOwnerSerializer

from shared.exceptions import CustomException
from shared.services import get_subscription
from file_uploads.models import ItemImage


def change_stock(product, quantity, operation):
    try:
        product = Product.objects.get(id=product)
    except Product.DoesNotExist:
        raise CustomException(
            'Product with ref id ' + ' does not exist.',
            status.HTTP_404_NOT_FOUND
        )

    if operation == 'SUB':
        if product.stock < quantity:
            raise CustomException(
                'The quantity of ' + product.name + ' exceeds stock levels.',
                status.HTTP_409_CONFLICT
            )

        if (product.stock - quantity) == 0 or (product.stock - quantity) < product.min_order_quantity:
            product.status = -2
            product.save()

        product.stock -= quantity
    else:
        product.stock += quantity

    product.save()
    

class ProductView(APIView):
    serializer_class = ProductSerializer

    def check_edit_name_is_unique(self, shop, name, ref_id):
        product = Product.objects.filter(shop__ref_id=shop, name__iexact=name).exclude(status=-1).first()

        if product is None:
            return True

        if ref_id != product.ref_id:
            return False

        return True

    def check_existing_product(self, shop, name):
        return Product.objects.filter(shop__ref_id=shop, name=name).exclude(status=-1).exists()

    def check_stock(self, product):
        stock = DigitalProduct.objects.filter(product=product).exclude(status=1).exclude(status=-1).count()
        product.stock = stock
        product.save()

    def add_keys_to_product(self, product, keys):
        delimiter = detect(
            keys,
            default='\n',
            whitelist=[',', '\n', ' ']
        )

        if delimiter is None:
            if keys.strip():
                DigitalProduct.objects.create(key=keys, product=product)
        else:
            keys_lines = keys.split(delimiter)
            for key_line in keys_lines:
                key_line.replace(' ', '')

                if key_line.strip():
                    DigitalProduct.objects.create(key=key_line, product=product)

        self.check_stock(product)

    def add_images_to_product(self, product, images):
        valid_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']

        for image in images:
            extension = os.path.splitext(image.name)[1][1:].lower()
            file_name = str(uuid4()) + '.' + extension

            if extension in valid_extensions:
                save_path = os.path.join('media', 'items', file_name)

                s3 = boto3.resource('s3')
                s3.Bucket('jkpay').put_object(Key=save_path, Body=image)

                ItemImage.objects.create(
                    name=file_name,
                    original_name=image.name,
                    path=os.path.join('/', save_path),
                    size=image.size,
                    item=product,
                )
            else:
                raise CustomException(
                    'Image file type is not supported (png, jpg, gif, webp)',
                    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                )

    def get(self, request, shop_ref=None, product_ref=None):
        products = None
        is_many = False

        if shop_ref is not None:
            try:
                products = Product.objects.filter(shop__ref_id=shop_ref).exclude(status=-1).order_by('name')
                is_many = True
            except Product.DoesNotExist:
                raise CustomException(
                    'Products for shop id ' + str(shop_ref) + ' were not found.',
                    status.HTTP_204_NO_CONTENT,
                )

        elif product_ref is not None:
            try:
                products = Product.objects.exclude(status=-1).get(ref_id=product_ref)
            except Product.DoesNotExist:
                raise CustomException(
                    'A product with id ' + str(product_ref) + ' was not found.',
                    status.HTTP_204_NO_CONTENT,
                )

        product_data = PublicProductOwnerSerializer(instance=products, many=is_many)

        data = {
            'success': True,
            'message': 'Product(s) that match your criteria were found.',
            'data': product_data.data
        }

        return Response(data, status=status.HTTP_200_OK)

    def post(self, request):
        product_data = request.data

        if product_data.get('shop') is None:
            raise CustomException(
                'Shop is required.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        elif product_data.get('name') is None:
            raise CustomException(
                'Name is required.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        elif product_data.get('price') is None:
            raise CustomException(
                'Price is required.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        context = {'request': request}
        serialized_data = self.serializer_class(data=product_data, context=context)
        is_valid = serialized_data.is_valid(raise_exception=True)

        if not is_valid:
            raise CustomException(
                'There was a problem creating a product.',
                status.HTTP_400_BAD_REQUEST
            )

        if self.check_existing_product(product_data.get('shop'), product_data.get('name')):
            raise CustomException(
                'Product name must be unique to your shop.',
                status.HTTP_409_CONFLICT,
            )

        product = serialized_data.create(serialized_data.data)

        if product_data.get('keys') is not None:
            self.add_keys_to_product(product, product_data.get('keys'))

        if request.FILES.getlist('images'):
            self.add_images_to_product(product, request.FILES.getlist('images'))

        data = {
            'success': True,
            'message': 'A product has been created.',
            'data': {
                'ref_id': product.ref_id,
                'name': product.name,
            },
        }

        return Response(data, status=status.HTTP_201_CREATED)

    def put(self, request, product_ref):
        product_data = request.data

        if product_ref is None:
            raise CustomException(
                'A product id must be provided.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        elif product_data.get('shop') is None:
            raise CustomException(
                'Shop is required.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        elif product_data.get('name') is None:
            raise CustomException(
                'Name is required.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        elif product_data.get('price') is None:
            raise CustomException(
                'Price is required.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        context = {'request': request}
        serialized_data = self.serializer_class(data=product_data, context=context)
        is_valid = serialized_data.is_valid(raise_exception=True)

        if not is_valid:
            raise CustomException(
                'There was a problem updating this product.',
                status.HTTP_400_BAD_REQUEST
            )

        is_unique = self.check_edit_name_is_unique(product_data.get('shop'), product_data.get('name'), product_ref)
        if not is_unique:
            raise CustomException(
                'Product name must be unique to your shop.',
                status.HTTP_409_CONFLICT,
            )

        try:
            product_to_update = Product.objects.get(ref_id=product_ref)
            product = serialized_data.update(product_to_update, serialized_data.data)
        except Product.DoesNotExist:
            raise CustomException(
                'A product with id ' + str(product_ref) + ' was not found.',
                status.HTTP_404_NOT_FOUND,
            )

        if product_data.get('keys') is not None:
            self.add_keys_to_product(product, product_data.get('keys'))

        if request.FILES.getlist('images'):
            self.add_images_to_product(product, request.FILES.getlist('images'))

        data = {
            'success': True,
            'message': 'Product ' + str(product_ref) + ' has been updated.',
            'data': {
                'ref_id': product.ref_id,
                'name': product.name,
            },
        }

        return Response(data, status=status.HTTP_200_OK)

    def delete(self, request, product_ref=None, digital_ref=None):
        data = None

        if product_ref is None and digital_ref is None:
            raise CustomException(
                'A product id or key id must be provided.',
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        if product_ref is not None:
            try:
                product = Product.objects.get(ref_id=product_ref)
                product.status = -1
                product.save()
            except Product.DoesNotExist:
                raise CustomException(
                    'There was an issue deleting product ' + str(product_ref) + '.',
                    status.HTTP_400_BAD_REQUEST,
                )

            data = {
                'success': True,
                'message': 'A product with id ' + str(product_ref) + ' was deleted.',
                'data': {},
            }
        if digital_ref is not None:
            try:
                key = DigitalProduct.objects.get(ref_id=digital_ref)
                key.status = -1
                key.save()

                self.check_stock(key.product)
            except Product.DoesNotExist:
                raise CustomException(
                    'There was an issue deleting key ' + str(digital_ref) + '.',
                    status.HTTP_400_BAD_REQUEST,
                )

            data = {
                'success': True,
                'message': 'A digital product with id ' + str(digital_ref) + ' was deleted.',
                'data': {},
            }

        return Response(data, status=status.HTTP_204_NO_CONTENT)
