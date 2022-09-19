from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from uuid import uuid4

import os
import stripe

from orders.models import Order
from orders.serializers import OrderStatusSerializer
from payments.models import PaymentProvider, Payment
from payments.serializers import PaymentSerializer, PaymentSessionSerializer
from payments.views import save_payment, save_payment_session, send_virtual_product_email
from products.views import change_stock
from shared.exceptions import CustomException
from shared.services import get_order_fees


class PaymentStripeView(APIView):
    permission_classes = [AllowAny]
    serializer_class = PaymentSessionSerializer

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
            order = Order.objects.get(ref_id=order_data['order_ref'])
        except Order.DoesNotExist:
            raise CustomException(
                'Could not find an order with ref id ' + order_data['order_ref'] + '.',
                status.HTTP_404_NOT_FOUND,
            )

        try:
            stripe_account = PaymentProvider.objects.get(shop__ref_id=order_data['shop_ref'], provider=1, status=1)
        except PaymentProvider.DoesNotExist:
            raise CustomException(
                'A connected Stripe account could not be found.',
                status.HTTP_404_NOT_FOUND
            )

        if not stripe_account.provider_data['details_submitted'] or not stripe_account.provider_data['charges_enabled']:
            raise CustomException(
                'A Stripe account was found but the onboarding step was not completed.',
                status.HTTP_403_FORBIDDEN
            )

        create_intent = stripe.PaymentIntent.create(
            amount=order.total,
            currency=order.currency,
            application_fee_amount=get_order_fees(order.total, order_data['shop_ref'], 1),
            stripe_account=stripe_account.provider_data['id'],
            automatic_payment_methods={
                'enabled': True,
            },
            payment_method_options={
                'card': {
                    'capture_method': 'manual',
                }
            },
            metadata={
                'stripe_account': stripe_account.provider_data['id'],
                'order_ref': order_data['order_ref'],
                'email': order_data['email']
            },
        )

        data = {
            'success': True,
            'message': 'Stripe payment intent created successfully.',
            'data': {
                'client_secret': create_intent['client_secret'],
                'account_id': stripe_account.provider_data['id'],
            },
        }

        return Response(data, status.HTTP_200_OK)


class PaymentStripeIpnView(APIView):
    permission_classes = [AllowAny]

    def verify_webhook(self, request):
        webhook_secret = os.environ['STRIPE_PAYMENT_WEBHOOK__CONNECT']
        signature = request.headers['STRIPE_SIGNATURE']

        try:
            event = stripe.Webhook.construct_event(payload=request.body, sig_header=signature, secret=webhook_secret)
        except ValueError:
            return False
        except stripe.error.SignatureVerificationError:
            return False

        return event

    def post(self, request):
        accepted_webhooks = (
            'payment_intent.payment_failed',
            'payment_intent.canceled',
            'payment_intent.created',
            'payment_intent.requires_action',
            'payment_intent.partially_funded',
            'payment_intent.amount_capturable_updated',
            'payment_intent.processing',
            'payment_intent.succeeded'
        )

        event = self.verify_webhook(request)
        if not event:
            data = {
                'success': False,
                'message': 'There was an error verifying the webhook signature.',
                'data': {}
            }

            return Response(data, status=status.HTTP_403_FORBIDDEN)

        if event['type'] in accepted_webhooks:
            instance = OrderStatusSerializer()
            webhook_data = event['data']['object']
            order = Order.objects.get(ref_id=webhook_data['metadata']['order_ref'])

            match event['type']:
                case 'payment_intent.payment_failed':
                    save_payment(1, webhook_data, order, True)
                    OrderStatusSerializer.create(instance, {'order': order, 'status': -2})

                case 'payment_intent.canceled':
                    save_payment(1, webhook_data, order, True)

                case 'payment_intent.amount_capturable_updated':
                    save_payment_session(1, webhook_data, event['type'], order)

                    stripe.PaymentIntent.capture(
                        webhook_data['id'],
                        stripe_account=webhook_data['metadata']['stripe_account']
                    )

                case 'payment_intent.succeeded':
                    OrderStatusSerializer.create(instance, {'order': order, 'status': 1})
                    OrderStatusSerializer.create(instance, {'order': order, 'status': 2})

                    save_payment(1, webhook_data, order, False)

                    for order_item in order.items.all():
                        change_stock(order_item.product_id, order_item.quantity, 'SUB')

                    send_virtual_product_email(webhook_data['metadata']['email'], order)

                    OrderStatusSerializer.create(instance, {'order': order, 'status': 3})

                case _:
                    save_payment_session(1, webhook_data, event['type'], order)

        data = {
            'success': True,
            'message': 'IPN successfully recieved.',
            'data': {},
        }

        return Response(data, status.HTTP_200_OK)
