from django.utils import timezone
from django.conf import settings
from django.template.loader import render_to_string
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from uuid import uuid4

import os
import stripe

from .models import PaymentProvider
from .serializers import PublicPaymentProviderSerializer, PaymentSessionSerializer, PaymentSerializer

from blacklists.models import Blacklist
from orders.serializers import OrderItemStatusSerializer
from products.models import DigitalProduct
from products.serializers import PublicProductSerializer
from shared.exceptions import CustomException
from shared.services import send_mailgun_email, get_url
from shops.models import Shop
from users.models import User
from users.serializers import PublicUserInfoSerializer


def get_stripe_status(provider_status):
    match provider_status:
        case 'payment_intent.payment_failed':
            stripe_status = -2
        case 'payment_intent.canceled':
            stripe_status = -1
        case 'payment_intent.created' | 'payment_intent.processing':
            stripe_status = 0
        case 'payment_intent.requires_action' | 'payment_intent.partially_funded':
            stripe_status = 1
        case 'payment_intent.amount_capturable_updated' | 'payment_intent.succeeded':
            stripe_status = 2
        case _:
            stripe_status = -2

    return stripe_status


def get_paypal_status(provider_status):
    match provider_status:
        case 'PAYMENT.CAPTURE.DENIED':
            paypal_status = -2
        case 'PAYMENT.CAPTURE.REVERSED' | 'PAYMENT.CAPTURE.REFUNDED' | 'PAYMENT.AUTHORIZATION.VOIDED':
            paypal_status = -1
        case 'PAYMENT.AUTHORIZATION.CREATED' | 'PAYMENT.CAPTURE.PENDING':
            paypal_status = 0
        case 'PAYMENT.CAPTURE.COMPLETED':
            paypal_status = 2
        case _:
            paypal_status = -2

    return paypal_status


def get_btcpay_status(provider_status):
    match provider_status:
        case 'InvoiceInvalid':
            crypto_status = -2
        case 'InvoiceExpired':
            crypto_status = -1
        case 'InvoiceCreated':
            crypto_status = 0
        case 'InvoiceReceivedPayment' | 'InvoicePaymentSettled':
            crypto_status = 1
        case 'InvoiceProcessing' | 'InvoiceSettled':
            crypto_status = 2
        case _:
            crypto_status = -2

    return crypto_status


def save_payment(provider, provider_data, order, canceled=False):
    payment_data = {
        'provider': provider,
        'captured_at': timezone.now() if canceled is False else None,
        'canceled_at': timezone.now() if canceled is True else None,
        'provider_data': provider_data,
        'ref_id': uuid4(),
    }

    context = {'order': order}
    serialized_data = PaymentSerializer(data=payment_data, context=context)
    is_valid = serialized_data.is_valid(raise_exception=True)

    if not is_valid:
        raise CustomException(
            'There was a problem saving the payment.',
            status.HTTP_400_BAD_REQUEST
        )

    serialized_data.create(serialized_data.data)


def save_payment_session(provider, provider_data, provider_status, order):
    match provider:
        case 0:
            session_status = get_paypal_status(provider_status)
        case 1:
            session_status = get_stripe_status(provider_status)
        case 2:
            session_status = get_btcpay_status(provider_status)
        case _:
            session_status = -2

    session_data = {
        'provider': provider,
        'provider_data': provider_data,
        'status': session_status,
    }

    serialized_data = PaymentSessionSerializer(data=session_data)
    is_valid = serialized_data.is_valid(raise_exception=True)

    if not is_valid:
        raise CustomException(
            'There was a problem saving the payment session.',
            status.HTTP_400_BAD_REQUEST
        )

    serialized_data.create(serialized_data.data, order=order)


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

        product_data = PublicProductSerializer(order_item.product).data

        product = {
            'name': product_data.get('name'),
            'key': keys,
            'price': order_item.price / 100,
            'quantity': order_item.quantity,
            'main_image': product_data.get('images')[0]['path'] if product_data.get('images') else '',
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
        'order_total': total / 100,
        'currency': order.currency,
        'shop_name': order.shop.name
    }

    email_subject = order.shop.name + ' Order Complete'
    email_body = render_to_string(
        os.path.join(settings.BASE_DIR, 'templates', 'emails', 'order_complete.jinja2'),
        context
    )

    send_mailgun_email(email_address, email_subject, email_body, 'order')


class PaymentProviderView(APIView):
    permission_classes = [AllowAny]
    serializer_class = PublicPaymentProviderSerializer

    def start_stripe_onboarding(self, shop):
        onboarded_data = PaymentProvider.objects.get(shop=shop.id, provider=1)

        if onboarded_data:
            stripe_account_id = onboarded_data.provider_data['id']
            onboarded_data.status = 1
            onboarded_data.save()
        else:
            stripe_account = stripe.Account.create(
                type='standard',
                country=shop.country.iso_2,
                metadata={
                    'shop_ref': shop.ref_id
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
            refresh_url=get_url('/dashboard/settings'),
            return_url=get_url('/dashboard/settings'),
            type="account_onboarding",
        )

        return account_link

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

        providers = PaymentProvider.objects.filter(shop=shop).exclude(status=-1)
        provider_data = self.serializer_class(providers, many=True).data

        combined_provider_data = {}
        for data in provider_data:
            combined_provider_data.update(data)

        data = {
            'success': True,
            'message': 'Payment provider(s) for shop ' + str(shop_ref) + ' were successfully retrieved.',
            'data': combined_provider_data,
        }

        return Response(data, status=status.HTTP_200_OK)

    def post(self, request, shop_ref):
        provider_data = request.data
        account_link = None

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

        for key in provider_data:
            if key == 'stripe':
                account_link = self.start_stripe_onboarding(shop)
            else:
                PaymentProvider.objects.update_or_create(
                    shop_id=shop.id,
                    provider=0 if key == 'email' else 2,

                    defaults={
                        'shop_id': shop.id,
                        'status': 1 if provider_data.get(key) != '' else -1,
                        'provider_data': {
                            key: provider_data.get(key)
                        },
                    }
                )

        data = {
            'success': True,
            'message': 'Provider(s) successfully saved.',
            'data': account_link if account_link else {},
        }

        return Response(data, status=status.HTTP_200_OK)

    def delete(self, request, shop_ref):
        provider_data = request.data

        if shop_ref is None:
            raise CustomException(
                'An shop id must be provided.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        try:
            provider = PaymentProvider.objects.get(shop__ref_id=shop_ref, provider=provider_data.get('provider'))
            provider.status = -1
            provider.save()
        except PaymentProvider.DoesNotExist:
            raise CustomException(
                'A payment provider for shop with a ref id ' + str(shop_ref) + ' was not found.',
                status.HTTP_404_NOT_FOUND,
            )

        data = {
            'success': True,
            'message': 'A payment provider for shop with a ref id ' + str(shop_ref) + ' was deleted.',
            'data': {},
        }

        return Response(data, status=status.HTTP_204_NO_CONTENT)


class PaymentProviderStripeIpn(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        webhook_secret = os.environ['STRIPE_ACCOUNT_WEBHOOK__CONNECT']

        if not webhook_secret:
            data = {
                'success': False,
                'message': 'Webhook secret was not provided.',
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
