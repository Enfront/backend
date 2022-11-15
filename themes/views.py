from django.utils.text import slugify
from django.middleware.csrf import get_token
from django.http import HttpResponse, HttpResponseRedirect
from django.db.models import Q

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from uuid import uuid4
from babel.numbers import get_currency_symbol

import os
import boto3
import botocore
import json
import html

from groups.models import Collection
from .models import Theme, ThemeConfiguration
from .serializers import PublicThemeSerializer, ThemeConfigurationSerializer

from api.jinja2 import environment
from shops.models import Shop
from shops.serializers import PublicShopSerializer
from products.models import Product
from products.serializers import PublicProductSerializer
from customers.models import Customer
from customers.serializers import PublicCustomerInfoSerializer
from shared.exceptions import CustomException
from shared.services import get_form_errors, reset_form_errors, get_url
from carts.views import get_users_cart, get_users_cart_items, get_cart_total


class ThemeView(APIView):
    def get(self, request, theme_ref=None):
        if theme_ref is not None:
            try:
                theme = Theme.objects.get(ref_id=theme_ref)
                theme_data = PublicThemeSerializer(theme).data
            except Theme.DoesNotExist:
                raise CustomException(
                    'Theme template does not exist.',
                    status.HTTP_404_NOT_FOUND
                )

            data = {
                'success': True,
                'message': 'Theme ' + str(theme_ref) + ' successfully retrieved.',
                'data': theme_data,
            }

            return Response(data, status=status.HTTP_200_OK)

        themes = Theme.objects.filter(Q(status=1) | (Q(status=0) & Q(developer=request.user.pk)))
        themes_data = PublicThemeSerializer(themes, many=True).data

        data = {
            'success': True,
            'message': 'Themes have been successfully retrieved.',
            'data': themes_data,
        }

        return Response(data, status=status.HTTP_200_OK)


class ThemeConfigurationView(APIView):
    serializer_class = ThemeConfigurationSerializer

    def check_for_active_theme(self, user, shop_ref):
        try:
            active_theme = ThemeConfiguration.objects.get(shop__owner=user, shop__ref_id=shop_ref, status=1)
            active_theme.status = 0
            active_theme.save()
        except ThemeConfiguration.DoesNotExist:
            return

    def get(self, request, shop_ref=None, theme_ref=None):
        if shop_ref is None:
            raise CustomException(
                'Shop ID is required in the URL.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        elif theme_ref is None:
            raise CustomException(
                'Theme ID is required in the URL.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        try:
            theme_config = ThemeConfiguration.objects.get(
                shop__owner=request.user, theme__ref_id=theme_ref, shop__ref_id=shop_ref
            )

            if theme_config.config_status == 1:
                save_path = os.path.join('themes', 'configurations', theme_config.file_name)

                s3 = boto3.client('s3')
                config = s3.get_object(Bucket='jkpay', Key=save_path)
                contents = config['Body'].read().decode()
                json_content = json.loads(contents)
            else:
                json_content = None
        except ThemeConfiguration.DoesNotExist:
            # TODO: Maybe replace with creation of config file
            raise CustomException(
                'A theme configuration was not found for shop ' + str(shop_ref) + '.',
                status.HTTP_204_NO_CONTENT
            )

        data = {
            'success': True,
            'message': 'Theme configuration successfully found.',
            'data': json_content,
        }

        return Response(data, status=status.HTTP_200_OK)

    def post(self, request):
        config_data = request.data

        if config_data.get('shop') is None:
            raise CustomException(
                'Shop ID is required.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        elif config_data.get('theme') is None:
            raise CustomException(
                'Theme ID is required.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        elif config_data.get('status') is None:
            raise CustomException(
                'Status is required.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        context = {'request': request}
        serialized_data = self.serializer_class(data=config_data, context=context)
        is_valid = serialized_data.is_valid(raise_exception=True)

        if not is_valid:
            data = {
                'success': False,
                'message': 'Theme config data is not valid.',
                'data': {}
            }

            return Response(data, status=status.HTTP_400_BAD_REQUEST)

        self.check_for_active_theme(request.user, config_data.get('shop'))

        existing_config = ThemeConfiguration.objects.filter(
            shop__owner=request.user,
            shop__ref_id=config_data.get('shop'),
            theme__ref_id=config_data.get('theme'),
        ).first()

        activate_config = 1 if config_data.get('config') else 0

        if existing_config:
            serialized_data.partial_update(existing_config, config_data, activate_config=activate_config)
            save_path = os.path.join('themes', 'configurations', existing_config.file_name)
        else:
            theme_config = serialized_data.create(serialized_data.data, activate_config=activate_config)
            save_path = os.path.join('themes', 'configurations', theme_config.file_name)

        if config_data.get('config') is not None:
            s3 = boto3.resource('s3')
            s3.Bucket('jkpay').put_object(Key=save_path, Body=html.escape(config_data.get('config'), quote=False))

        data = {
            'success': True,
            'message': 'Theme configuration successfully applied.',
            'data': {},
        }

        return Response(data, status=status.HTTP_200_OK)


class ThemeSettingsView(APIView):
    def get(self, request, theme_ref):
        if theme_ref is None:
            raise CustomException(
                'Theme ID is required.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        s3 = boto3.client('s3')

        try:
            theme = Theme.objects.get(ref_id=theme_ref)
            slugged_theme_name = slugify(theme.name)
            settings_path = os.path.join(
                'themes', 'templates', 'official', slugged_theme_name, 'config', 'settings.json'
            )

            theme_settings = s3.get_object(Bucket='jkpay', Key=settings_path)
            settings_content = theme_settings['Body'].read().decode()
        except Theme.DoesNotExist:
            raise CustomException(
                'Settings for theme ' + str(theme_ref) + ' were not found.',
                status.HTTP_404_NOT_FOUND,
            )

        data = {
            'success': True,
            'message': 'Theme settings successfully found.',
            'data': json.loads(settings_content),
        }

        return Response(data, status=status.HTTP_200_OK)


class ThemeTemplateView(APIView):
    permission_classes = [AllowAny]

    def money(self, data, currency):
        if not currency:
            return 'No currency provided'

        return currency + str(format(data / 100, '.02f'))

    def product_url(self, product_name):
        if not product_name:
            return None

        return '/product/' + slugify(product_name)

    def media_url(self, data):
        if isinstance(data, str):
            return 'https://jkpay.s3.us-east-2.amazonaws.com' + data

        if not data or not data.get('path'):
            return None

        return 'https://jkpay.s3.us-east-2.amazonaws.com' + data.get('path')

    def asset_url(self, asset_name, theme_ref=None, official=None):
        try:
            theme = Theme.objects.get(ref_id=theme_ref)
        except Theme.DoesNotExist:
            return HttpResponseRedirect(get_url('/404'))

        theme_template_path = os.path.join(
            'themes',
            'templates',
            ('official' if official is not None else ''),
            slugify(theme.name),
            'assets'
        )

        return 'https://jkpay.s3.us-east-2.amazonaws.com/' + theme_template_path + '/' + asset_name

    def get_header_content(self, is_editor):
        editor_file = open('templates/editor.html', 'r')

        if is_editor is None:
            recaptcha_file = open('templates/recaptcha.html', 'r')

            return editor_file.read() + recaptcha_file.read()

        return editor_file.read()

    def get_products(self, shop_ref, collection_slug=None):
        if collection_slug is not None:
            try:
                collection = Collection.objects.get(slug=collection_slug)
            except Collection.DoesNotExist:
                return []

            products = collection.products.all()
        else:
            products = Product.objects.filter(shop__ref_id=shop_ref, status=1).order_by('name')

        products_data = PublicProductSerializer(products, many=True).data
        return products_data

    def get_product(self, shop_ref, item_slug, cart=None):
        if item_slug is None:
            return None

        if item_slug == 'test':
            product = {
                'id': '8e8cf26e-0cde-4858-9b05-6b30573fa79c',
                'name': 'Torq Nutcracker',
                'description':
                    'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do '
                    'eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut '
                    'enim ad minim veniam, quis nostrud exercitation ullamco laboris '
                    'nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor '
                    'in reprehenderit in voluptate velit esse cillum dolore eu fugiat '
                    'nulla pariatur. Excepteur sint occaecat cupidatat non proident, '
                    'sunt in culpa qui officia deserunt mollit anim id est laborum.',
                'price': 250.00,
                'shop_id': str(shop_ref),
                'images': [{'id': 3, 'path': '/media/items/0b5458bc-5c33-45f5-85c7-74b229c820c9.jpeg'}],
                'min_order_quantity': 1,
                'max_order_quantity': 20,
            }

            return product

        try:
            product = Product.objects.get(shop__ref_id=shop_ref, slug=item_slug)
            product = PublicProductSerializer(product).data

            # change min order quantity if a user already has the item in their cart
            if cart is not None:
                for cart_item in cart['items']:
                    if product['min_order_quantity'] - cart_item['quantity'] <= 0:
                        product['min_order_quantity'] = 1

        except Product.DoesNotExist:
            return None

        return product

    def get_customer(self, user, user_cookie):
        if user.is_authenticated:
            try:
                user_object = Customer.objects.get(user__ref_id=user.ref_id)
                user_data = PublicCustomerInfoSerializer(user_object).data

                user = {
                    'id': user_data['user']['ref_id'],
                    'username': user_data['user']['username'],
                    'email': user_data['user']['email'],
                    'first_name': user_data['user']['first_name'],
                    'last_name': user_data['user']['last_name'],
                }
            except Customer.DoesNotExist:
                user = {
                    'id': uuid4() if user_cookie is None else user_cookie,
                    'username': None,
                    'email': None,
                    'first_name': None,
                    'last_name': None,
                }
        else:
            user = {
                'id': uuid4() if user_cookie is None else user_cookie,
                'username': None,
                'email': None,
                'first_name': None,
                'last_name': None,
            }

        return user

    def get_cart(self, cart_cookie):
        cart = get_users_cart(cart_cookie)
        cart_items = get_users_cart_items(cart)
        total = get_cart_total(cart_items)

        cart_quantity = 0
        for cart_item in cart_items:
            cart_quantity += 1 * cart_item['quantity']

        all_cart = {
            "items": cart_items,
            "items_amount": cart_quantity,
            "total": total
        }

        return all_cart

    def get_custom_filters(self):
        jinja_environment = environment()
        jinja_environment.filters['slugify'] = slugify
        jinja_environment.filters['product_url'] = self.product_url
        jinja_environment.filters['asset_url'] = self.asset_url
        jinja_environment.filters['media_url'] = self.media_url
        jinja_environment.filters['money'] = self.money

        return jinja_environment

    def get_reset_password_data(self, request):
        reset_data = {
            'ref_id': request.query_params.get('ref_id'),
            'token': request.query_params.get('token')
        }

        return reset_data

    def add_item_details_to_config(self, config):
        for key in config:
            if isinstance(config[key], dict) and 'item' in config[key]:
                try:
                    product = Product.objects.get(ref_id=config[key]['id'])
                    product_data = PublicProductSerializer(product).data

                    config[key]['name'] = product_data['name']
                    config[key]['price'] = product_data['price']
                    config[key]['slug'] = product_data['slug']
                    config[key]['images'] = product_data['images']
                    config[key]['available'] = product_data['available']
                except Product.DoesNotExist:
                    return None

    def get(self, request, page=None, item_slug=None):
        try:
            shop = Shop.objects.get(domain=request.get_host())
            shop_data = PublicShopSerializer(shop).data
        except Shop.DoesNotExist:
            return HttpResponseRedirect(get_url('/404'))

        if request.query_params.get('themeId') is None:
            try:
                theme = Theme.objects.get(ref_id=shop_data['current_theme']['ref_id'])
            except Theme.DoesNotExist:
                raise CustomException(
                    'Theme with ref id ' + str(shop_data['current_theme']['ref_id']) + ' could not be found.',
                    status.HTTP_404_NOT_FOUND,
                )
        else:
            try:
                theme = Theme.objects.get(ref_id=request.query_params.get('themeId'))
            except Theme.DoesNotExist:
                raise CustomException(
                    'Theme with ref id ' + str(request.query_params.get('themeId')) + ' could not be found.',
                    status.HTTP_404_NOT_FOUND,
                )

        if shop.status == 0 and request.query_params.get('editor') is None:
            return HttpResponseRedirect(get_url('/closed'))

        if page == 'product' and self.get_product(shop.ref_id, item_slug) is None:
            return HttpResponseRedirect(get_url('/404'))

        user_cookie = request.COOKIES.get('_enfront_uid')
        cart_cookie = request.COOKIES.get('_enfront_cid')
        cart = self.get_cart(cart_cookie)

        template_data = {
            'cart': cart,
            'csrf_token': get_token(request),
            'currency': get_currency_symbol(shop.currency),
            'product': self.get_product(shop.ref_id, item_slug, cart),
            'products': self.get_products(shop.ref_id, item_slug),
            'required_header_content': self.get_header_content(request.query_params.get('editor')),
            'shop_ref': shop.ref_id,
            'shop_name': shop.name,
            'theme_id': theme.ref_id,
            'user': self.get_customer(request.user, user_cookie),
            'form_errors': get_form_errors(),
            'reset_data': self.get_reset_password_data(request),
        }

        s3 = boto3.client('s3')

        try:
            theme_template_path = os.path.join(
                'themes',
                'templates',
                'official',
                slugify(theme.name),
                ('index' if page is None else page) + '.jinja2',
            )

            jinja_file = s3.get_object(Bucket='jkpay', Key=theme_template_path)
            jinja_file_decoded = jinja_file['Body'].read().decode('utf_8')
            jinja_environment = self.get_custom_filters()
            jinja_template = jinja_environment.from_string(jinja_file_decoded)
        except s3.exceptions.NoSuchKey:
            return HttpResponseRedirect(get_url('/404'))

        try:
            config = ThemeConfiguration.objects.get(
                theme__ref_id=theme.ref_id,
                shop__ref_id=shop_data['ref_id']
            )
        except ThemeConfiguration.DoesNotExist:
            raise CustomException(
                'A theme configuration does not exist.',
                status.HTTP_404_NOT_FOUND,
            )

        if config.file_name != '':
            theme_config_path = os.path.join(
                'themes',
                'configurations',
                config.file_name
            )

            try:
                config_file = s3.get_object(Bucket='jkpay', Key=theme_config_path)
                config_file_decoded = json.load(config_file['Body'])
                self.add_item_details_to_config(config_file_decoded)

                rendered_template = jinja_template.render(template_data | config_file_decoded)
            except botocore.exceptions.ClientError:
                rendered_template = jinja_template.render(template_data)
        else:
            rendered_template = jinja_template.render(template_data)

        reset_form_errors()

        response = HttpResponse(rendered_template)

        if user_cookie is None:
            response.set_cookie('_enfront_uid', template_data['user']['id'], 604800)

        return response
