from django.conf import settings
from django.utils import timezone
from django.utils.http import urlencode
from django.forms.models import model_to_dict
from django.template.loader import render_to_string
from django.core.exceptions import ValidationError

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from paypalcheckoutsdk.core import PayPalHttpClient, LiveEnvironment, SandboxEnvironment
from paypalcheckoutsdk.payments import AuthorizationsCaptureRequest, AuthorizationsVoidRequest
from paypalcheckoutsdk.orders import OrdersCreateRequest, OrdersCaptureRequest, OrdersAuthorizeRequest
from uuid import uuid4

import decimal
import hashlib
import hmac
import json
import math
import sys
import os
import stripe
import urllib.error
import urllib.parse
import urllib.request

from .models import PaymentProvider
from .serializers import PaymentSerializer, PaymentSessionSerializer

from orders.models import Order
from orders.serializers import (
    PublicOrderCheckoutSerializer,
    OrderStatusSerializer,
    OrderSerializer,
    OrderItemStatusSerializer
)

from blacklists.models import Blacklist
from shops.models import Shop
from shared.services import send_mailgun_email, get_subscription
from shared.exceptions import CustomException
from products.views import change_stock
from products.models import DigitalProduct
from products.serializers import PublicProductSerializer
from users.serializers import PublicUserInfoSerializer
from users.models import User

stripe.api_key = os.environ['STRIPE_KEY']


def check_banned_email(email, shop):
    return Blacklist.objects.filter(paypal_email=email, shop=shop).exists()


def send_virtual_product_email(email_address, order):
    total = 0
    order_items_detailed = []

    for order_item in order.items.all():
        keys = []

        for _ in range(0, order_item.quantity):
            key = DigitalProduct.objects.filter(product=order_item.product, status=0).first()
            key.status = 1
            key.recipient_email = email_address
            key.save()

            order_item.purchased_keys.add(key)
            keys.append(key.key)

            total += order_item.price

        instance = OrderItemStatusSerializer()
        OrderItemStatusSerializer.create(instance, {'item': order_item, 'status': 1})
        OrderItemStatusSerializer.create(instance, {'item': order_item, 'status': 2})

        order_item.current_status = 2
        order_item.save()

        product_data = PublicProductSerializer(order_item.product).data
        product = {
            'name': product_data.get('name'),
            'key': keys,
            'price': order_item.price,
            'quantity': order_item.quantity,
            # 'main_image': product_data.get('images')[0].path if product_data.get('images') else '',
            'main_image': '',
        }

        order_items_detailed.append(product)

    full_name = 'Anonymous'
    buyer = User.objects.filter(id=order.customer.id).first()

    if buyer:
        user = PublicUserInfoSerializer(buyer).data

        if user.get('first_name') is not None and user.get('last_name') is not None:
            full_name = user.get('first_name') + ' ' + user.get('last_name')

    context = {
        'full_name': full_name,
        'order_id': order.ref_id,
        'order_items': order_items_detailed,
        'order_total': total,
        'currency': order.currency,
        'shop_name': order.shop.name
    }

    email_subject = order.shop.name + ' Order Complete'
    email_body = render_to_string(
        os.path.join(settings.BASE_DIR, 'templates', 'emails', 'order_complete.jinja2'),
        context
    )

    send_mailgun_email(email_address, email_subject, email_body, 'order')


class PayPalClient:
    def __init__(self, *args, **kwargs):
        self.client_id = os.environ['PAYPAL_CLIENT_ID']
        self.client_secret = os.environ['PAYPAL_CLIENT_SECRET']

        """ Set up and return PayPal Python SDK environment with PayPal access credentials.
           This sample uses SandboxEnvironment. In production, use LiveEnvironment. """
        if os.environ['PAYPAL_ENVIRONMENT'] == 'LiveEnvironment':
            self.environment = LiveEnvironment(
                client_id=self.client_id,
                client_secret=self.client_secret
            )
        else:
            self.environment = SandboxEnvironment(
                client_id=self.client_id,
                client_secret=self.client_secret
            )

        """ Returns PayPal HTTP client instance with environment that has access
            credentials context. Use this instance to invoke PayPal APIs, provided the
            credentials have access. """
        self.client = PayPalHttpClient(self.environment)

    def object_to_json(self, json_data):
        # Function to print all json data in an organized readable manner
        result = {}
        if hasattr(json_data, '__dict__'):
            if sys.version_info[0] < 3:
                itr = json_data.__dict__.iteritems()
            else:
                itr = json_data.__dict__.items()

            for key, value in itr:
                # Skip internal attributes.
                if key.startswith('_'):
                    continue

                result[key] = self.array_to_json_array(value) if isinstance(value, list) else \
                    self.object_to_json(value) if not self.is_primittive(value) else \
                        value

        return result

    def array_to_json_array(self, json_array):
        result = []
        if isinstance(json_array, list):
            for item in json_array:
                result.append(self.object_to_json(item) if not self.is_primittive(item) else
                              self.array_to_json_array(item) if isinstance(item, list) else item)

        return result

    def is_primittive(self, data):
        return isinstance(data, str) or isinstance(data, bytes) or isinstance(data, int)


class PaymentsPayPalView(PayPalClient, APIView):
    permission_classes = [AllowAny]
    serializer_class = PaymentSessionSerializer

    def get_merchant_id(self, shop):
        try:
            paypal_account = PaymentProvider.objects.get(shop=shop, provider=0, status=1)
        except PaymentProvider.DoesNotExist:
            raise CustomException(
                'A PayPal account for a shop with the id ' + str(shop.ref_id) + ' could not be found.',
                status.HTTP_404_NOT_FOUND,
            )

        return paypal_account.provider_data['email']

    def prepare_paypal_items(self, order):
        item_request_body = []

        for order_item in order.items.all():
            item_request_body.append(
                {
                    'name': order_item.product.name,
                    'unit_amount': {
                        'currency_code': order.currency,
                        'value': str(order_item.price / 100)
                    },
                    'quantity': str(order_item.quantity),
                    'category': 'DIGITAL_GOODS'
                },
            )

        return item_request_body

    def build_request_body(self, order_ref, shop_ref):
        try:
            order = Order.objects.get(ref_id=order_ref)
            order_data = PublicOrderCheckoutSerializer(order).data
        except Order.DoesNotExist:
            raise CustomException(
                'Could not find an order with the id ' + str(order_ref) + '.',
                status.HTTP_404_NOT_FOUND,
            )

        try:
            shop = Shop.objects.get(ref_id=shop_ref)
        except Shop.DoesNotExist:
            raise CustomException(
                'Could not find a shop with the id ' + str(shop_ref) + '.',
                status.HTTP_404_NOT_FOUND,
            )

        return \
            {
                'intent': 'AUTHORIZE',
                'application_context': {
                    'brand_name': 'Enfront',
                    'shipping_preference': 'NO_SHIPPING',
                    'user_action': 'CONTINUE'
                },
                'purchase_units': [{
                    'invoice_id': order_ref,
                    'payee': {
                        'email': self.get_merchant_id(shop),
                    },
                    'amount': {
                        'currency_code': order_data['currency'],
                        'value': str(order_data['total'] / 100),
                        'breakdown': {
                            'item_total': {
                                'currency_code': order_data['currency'],
                                'value': str(order_data['total'] / 100),
                            },
                        }
                    },
                    'items': self.prepare_paypal_items(order),
                }]
            }

    def save_payment_session(self, intent, order):
        match intent['status']:
            case 'VOIDED':
                paypal_status = -1
            case 'CREATED':
                paypal_status = 0
            case 'SAVED | APPROVED | PAYER_ACTION_REQUIRED':
                paypal_status = 1
            case 'COMPLETED':
                paypal_status = 2
            case _:
                paypal_status = -2

        paypal_data = {
            'provider': 0,
            'provider_data': intent,
            'status': paypal_status
        }

        serialized_data = self.serializer_class(data=paypal_data)
        is_valid = serialized_data.is_valid(raise_exception=False)

        if not is_valid:
            raise CustomException(
                'There was a problem saving the payment session.',
                status.HTTP_400_BAD_REQUEST
            )

        serialized_data.create(serialized_data.data, order=order)

    def save_webhook(self, webhook_data, order, authorization=False):
        match webhook_data['status']:
            case 'VOIDED':
                paypal_status = -1
            case 'COMPLETED' if authorization:
                paypal_status = 1
            case 'CREATED':
                paypal_status = 1
            case 'SAVED | APPROVED | PAYER_ACTION_REQUIRED':
                paypal_status = 2
            case 'COMPLETED' if not authorization:
                paypal_status = 3
            case _:
                paypal_status = 0

        paypal_data = {
            'provider': 0,
            'captured_at': timezone.now(),
            'provider_data': webhook_data,
            'status': paypal_status,
            'ref_id': uuid4(),
        }

        context = {'order': order}
        serialized_data = PaymentSerializer(data=paypal_data, context=context)
        is_valid = serialized_data.is_valid(raise_exception=False)

        if not is_valid:
            raise CustomException(
                'There was an issue recieving the IPN.',
                status.HTTP_400_BAD_REQUEST
            )

        serialized_data.create(serialized_data.data)

    def get(self, request, paypal_id, order_ref):
        if paypal_id is None:
            raise CustomException(
                'PayPal ID must be in the query URL.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        elif order_ref is None:
            raise CustomException(
                'Order ID must be in the query URL.',
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        try:
            order = Order.objects.get(ref_id=order_ref)
        except Order.DoesNotExist:
            raise CustomException(
                'An Order with an ID of ' + str(order_ref) + ' could not be found.',
                status.HTTP_404_NOT_FOUND,
            )

        authorize_request = OrdersAuthorizeRequest(paypal_id)
        authorize_request.prefer('return=representation')
        authorize_response = self.client.execute(authorize_request)
        response_json = self.object_to_json(authorize_response.result)
        self.save_webhook(response_json, order, True)

        is_banned = check_banned_email(authorize_response.result.payer.email_address, order.shop)
        if is_banned:
            void_request = AuthorizationsVoidRequest(
                authorize_response.result.purchase_units[0].payments.authorizations[0].id
            )

            action_response = self.client.execute(void_request)
        else:
            capture_request = AuthorizationsCaptureRequest(
                authorize_response.result.purchase_units[0].payments.authorizations[0].id
            )

            capture_request.prefer('return=representation')
            action_response = self.client.execute(capture_request)

        response_json = self.object_to_json(action_response.result)
        self.save_webhook(response_json, order)

        instance = OrderStatusSerializer()
        if action_response.status_code == 204:
            order.current_status = -2
            order.save()

            OrderStatusSerializer.create(instance, {'order': order, 'status': -2})

            data = {
                'success': False,
                'message': 'This shop has blacklisted this user.',
                'data': {},
            }

            return Response(data, status.HTTP_403_FORBIDDEN)

        OrderStatusSerializer.create(instance, {'order': order, 'status': 1})
        OrderStatusSerializer.create(instance, {'order': order, 'status': 2})

        for order_item in order.items.all():
            change_stock(order_item.product_id, order_item.quantity, 'SUB')

        send_virtual_product_email(request.query_params.get('email'), order)

        OrderStatusSerializer.create(instance, {'order': order, 'status': 3})

        data = {
            'success': True,
            'message': 'PayPal Transaction successfully completed.',
            'data': {},
        }

        return Response(data, status.HTTP_200_OK)

    def post(self, request):
        paypal_data = request.data

        if paypal_data.get('order_ref') is None:
            raise CustomException(
                'An order id must be provided.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        elif paypal_data.get('shop_ref') is None:
            raise CustomException(
                'A shop id must be provided.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        try:
            order = Order.objects.get(ref_id=paypal_data.get('order_ref'))
        except Order.DoesNotExist:
            raise CustomException(
                'Could not find an order with ref id ' + str(paypal_data.get('order_ref')) + '.',
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        paypal_request = OrdersCreateRequest()
        paypal_request.prefer('return=representation')

        paypal_request.request_body(self.build_request_body(
            paypal_data.get('order_ref'),
            paypal_data.get('shop_ref')
        ))

        response = self.client.execute(paypal_request)
        response_json = self.object_to_json(response.result)
        self.save_payment_session(response_json, order)

        data = {
            'success': True,
            'message': 'PayPal payment intent completed successfully.',
            'data': {
                'id': response.result.id
            },
        }

        return Response(data, status.HTTP_201_CREATED)


class PaymentsStripeView(APIView):
    permission_classes = [AllowAny]
    serializer_class = PaymentSessionSerializer

    def save_payment_session(self, intent, order):
        match intent['status']:
            case 'canceled':
                stripe_status = -1
            case 'requires_payment_method' | 'requires_confirmation' | 'processing':
                stripe_status = 0
            case 'requires_action':
                stripe_status = 1
            case 'requires_capture' | 'succeeded':
                stripe_status = 2
            case _:
                stripe_status = -2

        stripe_data = {
            'provider': 1,
            'provider_data': intent,
            'status': stripe_status
        }

        serialized_data = self.serializer_class(data=stripe_data)
        is_valid = serialized_data.is_valid(raise_exception=False)

        if not is_valid:
            raise CustomException(
                'There was a problem saving the payment session.',
                status.HTTP_400_BAD_REQUEST
            )

        serialized_data.create(serialized_data.data, order=order)

    def post(self, request):
        order_data = request.data

        if order_data.get('order_ref') is None:
            raise CustomException(
                'An order id must be provided.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        elif order_data.get('shop_ref') is None:
            raise CustomException(
                'A shop id must be provided.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        elif order_data.get('email') is None:
            raise CustomException(
                'An email must be provided.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        try:
            order = Order.objects.get(ref_id=order_data.get('order_ref'))
            order_serialized_data = PublicOrderCheckoutSerializer(order).data
        except Order.DoesNotExist:
            raise CustomException(
                'Could not find an order with ref id ' + order_data.get('order_ref') + '.',
                status.HTTP_404_NOT_FOUND,
            )

        try:
            stripe_account = PaymentProvider.objects.get(
                shop__ref_id=order_data.get('shop_ref'),
                provider=1,
                status=1,
            )
        except PaymentProvider.DoesNotExist:
            raise CustomException(
                'A connected Stripe account could not be found.',
                status.HTTP_404_NOT_FOUND
            )

        if not stripe_account.provider_data['details_submitted'] or not \
                stripe_account.provider_data['charges_enabled']:
            raise CustomException(
                'A Stripe account was found but the onboarding step was not complete.',
                status.HTTP_403_FORBIDDEN
            )

        if check_banned_email(order_data.get('email'), order.shop):
            order.current_status = -2
            order.save()

            instance = OrderStatusSerializer()
            OrderStatusSerializer.create(instance, {'order': order, 'status': -2})

            data = {
                'success': False,
                'message': 'This shop has blacklisted this user.',
                'data': {},
            }

            return Response(data, status.HTTP_403_FORBIDDEN)

        shop_subscription = get_subscription(shop_ref=order_data.get('shop_ref'))
        subscription_fee = math.ceil((order_serialized_data.get('total') * shop_subscription['fee']))

        intent = stripe.PaymentIntent.create(
            amount=order_serialized_data.get('total'),
            currency=order_serialized_data.get('currency'),
            application_fee_amount=subscription_fee,
            stripe_account=stripe_account.provider_data['id'],
            automatic_payment_methods={
                'enabled': True,
            },
            metadata={
                'order_ref': order_data.get('order_ref'),
                'email': order_data.get('email')
            },
        )

        self.save_payment_session(intent, order)

        data = {
            'success': True,
            'message': 'Stripe payment intent created successfully.',
            'data': {
                'client_secret': intent['client_secret'],
                'account_id': stripe_account.provider_data['id'],
            },
        }

        return Response(data, status.HTTP_200_OK)


class PaymentsStripeIpnView(APIView):
    permission_classes = [AllowAny]
    serializer_class = PaymentSerializer

    def save_webhook(self, webhook_type, webhook_data, order):
        match webhook_type:
            case 'payment_intent.canceled':
                stripe_status = -1
            case 'payment_intent.payment_failed':
                stripe_status = 0
            case 'payment_intent.processing':
                stripe_status = 1
            case 'payment_intent.requires_action' | 'payment_intent.partially_funded':
                stripe_status = 2
            case 'payment_intent.succeeded':
                stripe_status = 3
            case _:
                stripe_status = 0

        stripe_data = {
            'provider': 1,
            'captured_at': timezone.now(),
            'provider_data': webhook_data,
            'status': stripe_status,
            'ref_id':  uuid4(),
        }

        context = {'order': order}
        serialized_data = self.serializer_class(data=stripe_data, context=context)
        is_valid = serialized_data.is_valid(raise_exception=False)

        if not is_valid:
            raise CustomException(
                'There was a problem recieving the IPN.',
                status.HTTP_400_BAD_REQUEST
            )

        serialized_data.create(serialized_data.data)

    def post(self, request):
        webhook_secret = os.environ['STRIPE_WEBHOOK']

        if webhook_secret:
            signature = request.META.get('HTTP_STRIPE_SIGNATURE')

            try:
                event = stripe.Webhook.construct_event(
                    payload=request.body, sig_header=signature, secret=webhook_secret
                )
            except ValueError:
                data = {
                    'success': False,
                    'message': 'Invalid Stripe Payload.',
                    'data': {}
                }

                return Response(data, status=status.HTTP_400_BAD_REQUEST)
            except stripe.error.SignatureVerificationError:
                data = {
                    'success': False,
                    'message': 'There was an error verifying the webhook signature.',
                    'data': {}
                }

                return Response(data, status=status.HTTP_403_FORBIDDEN)

            if (event['type'] == 'payment_intent.canceled' or
                    event['type'] == 'payment_intent.processing' or
                    event['type'] == 'payment_intent.payment_failed' or
                    event['type'] == 'payment_intent.requires_action' or
                    event['type'] == 'payment_intent.partially_funded' or
                    event['type'] == 'payment_intent.succeeded'):

                instance = OrderStatusSerializer()
                webhook_data = event['data']['object']
                order = Order.objects.get(ref_id=webhook_data['metadata']['order_ref'])

                self.save_webhook(event['type'], webhook_data, order)

                if event['type'] == 'payment_intent.canceled':
                    for order_item in order.items.all():
                        change_stock(order_item.product_id, order_item.quantity, 'ADD')

                    OrderStatusSerializer.create(instance, {'order': order, 'status': -2})
                elif event['type'] == 'payment_intent.succeeded':
                    OrderStatusSerializer.create(instance, {'order': order, 'status': 1})
                    OrderStatusSerializer.create(instance, {'order': order, 'status': 2})

                    for order_item in order.items.all():
                        change_stock(order_item.product_id, order_item.quantity, 'SUB')

                    send_virtual_product_email(webhook_data['metadata']['email'], order)

                    OrderStatusSerializer.create(instance, {'order': order, 'status': 3})

            data = {
                'success': True,
                'message': 'IPN successfully recieved.',
                'data': {},
            }

            return Response(data, status.HTTP_200_OK)


class PaymentsProviderPayPalView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, shop_ref):
        if shop_ref is None:
            raise CustomException(
                'An shop id must be provided.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        try:
            shop = Shop.objects.get(ref_id=shop_ref)
        except Shop.DoesNotExist:
            raise CustomException(
                'A shop with ref id ' + str(shop_ref) + ' was not found.',
                status.HTTP_404_NOT_FOUND
            )

        try:
            paypal_details = PaymentProvider.objects.exclude(status=-1).get(shop=shop, provider=0)
        except PaymentProvider.DoesNotExist:
            raise CustomException(
                'A PayPal account for shop with id ' + str(shop_ref) + ' was not found.',
                status.HTTP_204_NO_CONTENT,
            )

        data = {
            'success': True,
            'message': 'PayPal for shop ' + str(shop_ref) + ' successfully retrieved.',
            'data': {
                'email': paypal_details.provider_data['email'],
            },
        }

        return Response(data, status=status.HTTP_200_OK)

    def post(self, request, shop_ref):
        paypal_data = request.data

        if shop_ref is None:
            raise CustomException(
                'An shop id must be provided.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        try:
            shop = Shop.objects.get(ref_id=shop_ref)
        except Shop.DoesNotExist:
            raise CustomException(
                'A shop with ref id ' + str(shop_ref) + ' was not found.',
                status.HTTP_404_NOT_FOUND
            )

        PaymentProvider.objects.update_or_create(
            shop_id=shop.id,
            provider=0,

            defaults={
                'shop_id': shop.id,
                'status': 1,
                'provider_data': {
                    'email': paypal_data.get('email')
                },
            }
        )

        data = {
            'success': True,
            'message': 'PayPal account successfully saved.',
            'data': {},
        }

        return Response(data, status=status.HTTP_200_OK)


class PaymentsProviderStripeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, shop_ref):
        if shop_ref is None:
            raise CustomException(
                'A shop id must be provided',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        try:
            stripe_acc = PaymentProvider.objects.get(shop__ref_id=shop_ref, provider=1, status=1)
        except PaymentProvider.DoesNotExist:
            raise CustomException(
                'A Stripe account was not found.',
                status.HTTP_204_NO_CONTENT
            )

        if not stripe_acc.provider_data['details_submitted'] or not \
                stripe_acc.provider_data['charges_enabled']:
            raise CustomException(
                'A Stripe account was found but the onboarding step was not complete.',
                status.HTTP_403_FORBIDDEN
            )

        data = {
            'success': True,
            'message': 'A Stripe account was found and onboarded.',
            'data': {
                'id': stripe_acc.provider_data['id']
            },
        }

        return Response(data, status=status.HTTP_200_OK)

    def post(self, request, shop_ref):
        if shop_ref is None:
            raise CustomException(
                'An shop id must be provided.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        try:
            shop = Shop.objects.get(ref_id=shop_ref)
        except Shop.DoesNotExist:
            raise CustomException(
                'A shop with ref id ' + str(shop_ref) + ' was not found.',
                status.HTTP_404_NOT_FOUND
            )

        onboarded_data = PaymentProvider.objects.filter(shop=shop.id, provider=1, status=1).first()

        if onboarded_data:
            stripe_account_id = onboarded_data.provider_data['id']
        else:
            stripe_account = stripe.Account.create(
                type='standard',
                country=shop.country.iso_2,
                metadata={
                    'shop_ref': shop_ref
                }
            )

            PaymentProvider.objects.update_or_create(
                shop_id=shop.id,
                provider=1,

                defaults={
                    'shop_id': shop.id,
                    'status': 1,
                    'provider_data': stripe_account,
                }
            )

            stripe_account_id = stripe_account.id

        account_link = stripe.AccountLink.create(
            account=stripe_account_id,
            refresh_url="http://localhost/dashboard/settings",
            return_url="http://localhost/dashboard/settings",
            type="account_onboarding",
        )

        data = {
            'success': True,
            'message': 'A Stripe account for shop with ref id ' + str(shop_ref) + ' is awaiting connection.',
            'data': account_link,
        }

        return Response(data, status=status.HTTP_200_OK)

    def delete(self, request, shop_ref):
        if shop_ref is None:
            raise CustomException(
                'An shop id must be provided.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        try:
            stripe_details = PaymentProvider.objects.get(shop__ref_id=shop_ref, provider=1)
            stripe_details.status = -1
            stripe_details.save()
        except PaymentProvider.DoesNotExist:
            raise CustomException(
                'A stripe account for shop with ref id ' + str(shop_ref) + ' was not found.',
                status.HTTP_404_NOT_FOUND,
            )

        data = {
            'success': True,
            'message': 'A Stripe account for shop with ref id ' + str(shop_ref) + ' was deleted.',
            'data': {},
        }

        return Response(data, status=status.HTTP_204_NO_CONTENT)


class PaymentsProviderStripeIpn(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        webhook_secret = os.environ['STRIPE_WEBHOOK']

        if not webhook_secret:
            data = {
                'success': False,
                'message': 'Webhook secret was not provided..',
                'data': {}
            }

            return Response(data, status=status.HTTP_400_BAD_REQUEST)

        signature = request.META.get('HTTP_STRIPE_SIGNATURE')

        try:
            event = stripe.Webhook.construct_event(
                payload=request.body, sig_header=signature, secret=webhook_secret
            )

            event_data = event["data"]["object"]
        except ValueError:
            data = {
                'success': False,
                'message': 'Invalid Stripe Payload.',
                'data': {}
            }

            return Response(data, status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError:
            data = {
                'success': False,
                'message': 'There was an error verifying the webhook signature.',
                'data': {}
            }

            return Response(data, status=status.HTTP_403_FORBIDDEN)

        event_type = event['type']

        if event_type == 'account.updated':
            PaymentProvider.objects.update_or_create(
                shop__ref_id=event_data['metadata']['shop_ref'],
                provider=1,

                defaults={
                    'status': 1,
                    'provider_data': event_data,
                }
            )

            data = {
                'success': True,
                'message': 'A Stripe account was updated.',
                'data': {},
            }

            return Response(data, status=status.HTTP_200_OK)

        data = {
            'success': True,
            'message': 'A webhook was recieved but not needed.',
            'data': {},
        }

        return Response(data, status=status.HTTP_200_OK)
