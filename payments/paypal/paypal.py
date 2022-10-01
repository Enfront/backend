from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from paypalcheckoutsdk.core import PayPalHttpClient, LiveEnvironment, SandboxEnvironment
from paypalcheckoutsdk.payments import AuthorizationsCaptureRequest, AuthorizationsVoidRequest
from paypalcheckoutsdk.orders import OrdersCreateRequest, OrdersCaptureRequest, OrdersAuthorizeRequest
from uuid import uuid4

import requests
import sys
import os

from payments.models import PaymentProvider, PaymentSession
from payments.serializers import PaymentSerializer, PaymentSessionSerializer
from payments.views import check_banned_email, save_payment_session, save_payment, send_virtual_product_email
from products.views import change_stock
from orders.models import Order
from orders.serializers import PublicOrderCheckoutSerializer, OrderStatusSerializer
from shared.exceptions import CustomException
from shops.models import Shop


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


class PaymentPayPalView(PayPalClient, APIView):
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
                    'custom_id': order.email,
                    'payee': {
                        'email_address': self.get_merchant_id(shop),
                    },
                    'amount': {
                        'currency_code': order.currency,
                        'value': str(order.total / 100),
                        'breakdown': {
                            'item_total': {
                                'currency_code': order.currency,
                                'value': str(order.total / 100),
                            },
                        }
                    },
                    'items': self.prepare_paypal_items(order),
                }]
            }

    # authorize and capture a PayPal payment
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
        authorize_id = authorize_response.result.purchase_units[0].payments.authorizations[0].id

        response_json = self.object_to_json(authorize_response.result)
        response_status = response_json['status']

        if response_status != 'COMPLETED':
            raise CustomException(
                'There was an issue creating a PayPal authorization.',
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if check_banned_email(authorize_response.result.payer.email_address, order.shop):
            void_request = AuthorizationsVoidRequest(authorize_id)
            self.client.execute(void_request)

            data = {
                'success': False,
                'message': 'This shop has blacklisted this user.',
                'data': {},
            }

            return Response(data, status.HTTP_403_FORBIDDEN)

        capture_request = AuthorizationsCaptureRequest(authorize_id)
        capture_request.prefer('return=representation')
        self.client.execute(capture_request)

        data = {
            'success': True,
            'message': 'PayPal Transaction successfully completed.',
            'data': {},
        }

        return Response(data, status.HTTP_200_OK)

    # create a PayPal checkout session
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

        paypal_request = OrdersCreateRequest()
        paypal_request.prefer('return=representation')

        paypal_request.request_body(self.build_request_body(
            order_data['order_ref'],
            order_data['shop_ref']
        ))

        response = self.client.execute(paypal_request)

        data = {
            'success': True,
            'message': 'PayPal payment intent completed successfully.',
            'data': {
                'id': response.result.id
            },
        }

        return Response(data, status.HTTP_201_CREATED)


class PaymentPayPalIpnView(PayPalClient, APIView):
    permission_classes = [AllowAny]

    def verify_webhook(self, request):
        auth_algo = request.headers["paypal-auth-algo"]
        cert_url = request.headers["paypal-cert-url"]
        transmission_id = request.headers["paypal-transmission-id"]
        transmission_sig = request.headers["paypal-transmission-sig"]
        transmission_time = request.headers["paypal-transmission-time"]

        # since PayPal's execute function expects an object, we can fake it with type()
        # https://stackoverflow.com/a/24448351
        paypal_object = type('', (), {})()

        setattr(paypal_object, 'verb', 'POST')
        setattr(paypal_object, 'path', '/v1/notifications/verify-webhook-signature')
        setattr(paypal_object, 'headers', {'Content-Type': 'application/json'})
        setattr(paypal_object, 'body', {
            'auth_algo': auth_algo,
            'cert_url': cert_url,
            'transmission_id': transmission_id,
            'transmission_sig': transmission_sig,
            'transmission_time': transmission_time,
            'webhook_event': request.data,
            'webhook_id': os.environ['PAYPAL_WEBHOOK']
        })

        paypal_request = self.client.execute(paypal_object)
        if paypal_request.result['verification_status'] == 'FAILURE':
            return False

        return True

    def post(self, request):
        webhook_data = request.data
        accepted_webhooks = (
            'PAYMENT.CAPTURE.REVERSED',
            'PAYMENT.CAPTURE.REFUNDED',
            'PAYMENT.CAPTURE.DENIED',
            'PAYMENT.AUTHORIZATION.VOIDED',
            'PAYMENT.AUTHORIZATION.CREATED',
            'PAYMENT.CAPTURE.PENDING',
            'PAYMENT.CAPTURE.COMPLETED',
        )

        is_verified = self.verify_webhook(request)
        if not is_verified:
            data = {
                'success': False,
                'message': 'There was an error verifying the webhook signature.',
                'data': {}
            }

            return Response(data, status=status.HTTP_403_FORBIDDEN)

        if request.data['event_type'] in accepted_webhooks:
            instance = OrderStatusSerializer()
            order = Order.objects.get(ref_id=webhook_data['resource']['invoice_id'])

            match webhook_data['event_type']:
                case 'PAYMENT.CAPTURE.DENIED':
                    save_payment(0, webhook_data, order, True)
                    OrderStatusSerializer.create(instance, {'order': order, 'status': -2})

                case 'PAYMENT.AUTHORIZATION.VOIDED':
                    save_payment(0, webhook_data, order, True)

                case 'PAYMENT.CAPTURE.COMPLETED':
                    OrderStatusSerializer.create(instance, {'order': order, 'status': 1})
                    OrderStatusSerializer.create(instance, {'order': order, 'status': 2})

                    save_payment(0, webhook_data, order, False)

                    for order_item in order.items.all():
                        change_stock(order_item.product_id, order_item.quantity, 'SUB')

                    send_virtual_product_email(webhook_data['resource']['custom_id'], order)

                    OrderStatusSerializer.create(instance, {'order': order, 'status': 3})

                case _:
                    save_payment_session(0, webhook_data, webhook_data['event_type'], order)

        data = {
            'success': True,
            'message': 'An IPN has been recieved.',
            'data': {},
        }

        return Response(data, status.HTTP_200_OK)
