from django.utils import timezone
from django.template.loader import render_to_string
from django.http import HttpResponseRedirect

from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import APIException

from uuid import uuid4

import os
import requests
import stripe
import json
import time

from .models import Subscription
from .serializers import SubscriptionSerializer, SubscriptionPaymentSerializer, PublicSubscriptionSerializer

from shops.models import Shop
from users.models import User
from products.models import Product
from shared.services import get_url, get_subscription, get_total_fees
from shared.exceptions import CustomException

stripe.api_key = os.environ['STRIPE_KEY']


class SubscriptionStripeView(APIView):
    def get(self, request, user_ref, shop_ref):
        response = Subscription.objects.filter(user__ref_id=user_ref, provider=1).last()

        if not response:
            data = {
                'success': True,
                'message': 'No subcriptions have been found.',
                'data': {
                    'total_fees': get_total_fees(shop_ref)
                },
            }

            return Response(data, status=status.HTTP_200_OK)

        subscription_data = PublicSubscriptionSerializer(response, context={'shop_ref': shop_ref}).data

        data = {
            'success': True,
            'message': 'A subcription has been found.',
            'data': subscription_data,
        }

        return Response(data, status=status.HTTP_200_OK)

    def post(self, request):
        stripe_data = request.data

        try:
            price = stripe.Price.search(
                query="product: '" + stripe_data.get('plan_id') + "'",
                expand=['data.product']
            )

            checkout_session = stripe.checkout.Session.create(
                line_items=[{
                    'price': price.data[0].id,
                    'quantity': 1,
                }],
                metadata={
                    'user_ref': stripe_data.get('user_ref')
                },
                subscription_data={
                    'metadata': {
                        'user_ref': stripe_data.get('user_ref')
                    }
                },
                mode='subscription',
                client_reference_id=stripe_data.get('user_ref'),
                success_url=get_url('/dashboard/account'),
                cancel_url=get_url('/dashboard/account'),
            )

            data = {
                'success': True,
                'message': 'A payment session was successfully started.',
                'data': {
                    'checkout_url': checkout_session.url,
                },
            }

            return Response(data, status=status.HTTP_200_OK)
        except APIException:
            data = {
                'success': False,
                'message': 'There was an issue creating the payment session.',
                'data': {}
            }

            return Response(data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def patch(self, request):
        try:
            stripe_data = request.data
            saved_subscription = Subscription.objects.filter(user=request.user.pk, provider=1).last()
            subscription = stripe.Subscription.retrieve(saved_subscription.provider_data['id'])

            if stripe_data.get('reinstate') and not stripe_data.get('is_upgrade'):
                stripe.Subscription.modify(
                    subscription.id,
                    cancel_at_period_end=False
                )

                data = {
                    'success': True,
                    'message': 'Subscription was successfully reinstated',
                    'data': {},
                }

                return Response(data, status=status.HTTP_200_OK)

            new_price = stripe.Price.search(query="product: '" + stripe_data.get('plan_id') + "'")
            payment_method = stripe.PaymentMethod.retrieve(subscription.default_payment_method)
            proration_date = int(time.time())

            items = [{
                'id': subscription['items']['data'][0].id,
                'price': new_price['data'][0].id,
            }]

            if stripe_data.get('is_upgrade') and stripe_data.get('accept_proration') is False:
                invoice = stripe.Invoice.upcoming(
                    customer=saved_subscription.provider_data['customer'],
                    subscription=saved_subscription.provider_data['id'],
                    subscription_items=items,
                    subscription_proration_date=proration_date,
                    subscription_proration_behavior='always_invoice'
                )

                data = {
                    'success': True,
                    'message': 'Please accept the proration before continuing.',
                    'data': {
                        'proration_amount': invoice['total'],
                        'proration_date': proration_date,
                        'last4': payment_method['card']['last4']
                    },
                }

                return Response(data, status=status.HTTP_202_ACCEPTED)

            if stripe_data.get('is_upgrade') and stripe_data.get('accept_proration'):
                stripe.Subscription.modify(
                    subscription.id,
                    payment_behavior='pending_if_incomplete',
                    proration_behavior='always_invoice',
                    proration_date=stripe_data.get('proration_date'),
                    items=items,
                )

            if stripe_data.get('is_upgrade') is False:
                stripe.Subscription.modify(
                    subscription.id,
                    cancel_at_period_end=False,
                    proration_behavior='none',
                    items=items,
                    metadata={
                        'user_ref': stripe_data.get('user_ref')
                    }
                )

            data = {
                'success': True,
                'message': 'Subscription ' + saved_subscription.provider_data['id'] + ' was modified.',
                'data': {},
            }

            return Response(data, status=status.HTTP_200_OK)
        except APIException:
            data = {
                'success': False,
                'message': 'There was an issue modifying the subscription.',
                'data': {}
            }

            return Response(data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, subscription_id):
        try:
            stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True
            )

            data = {
                'success': True,
                'message': 'Subscription ' + subscription_id + ' was successfully cancelled.',
                'data': {},
            }

            return Response(data, status=status.HTTP_204_NO_CONTENT)
        except APIException:
            data = {
                'success': False,
                'message': 'There was an issue canceling the subscription.',
                'data': {}
            }

            return Response(data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SubscriptionStripeIpnView(APIView):
    permission_classes = [AllowAny]

    def save_webhook(self, user, sub_status, sub_name, webhook_data):
        match sub_status:
            case 'canceled' | 'incomplete_expired':
                stripe_status = -1
            case 'past_due' | 'unpaid' | 'incomplete':
                stripe_status = 0
            case 'active':
                stripe_status = 1
            case _:
                stripe_status = 0

        match sub_name:
            case 'prod_MJKvTG7CmI8LA4':
                subscription_tier = 1
            case 'prod_MJKvSCYjuoxCk2':
                subscription_tier = 2
            case 'prod_MJKuG1zUSJtSCl':
                subscription_tier = 3
            case _:
                subscription_tier = None

        stripe_data = {
            'user': user.pk,
            'started_at': timezone.now() if stripe_status == 1 else None,
            'canceled_at': timezone.now() if stripe_status == -1 else None,
            'provider': 1,
            'provider_data': webhook_data,
            'status': stripe_status,
            'subscription_tier': subscription_tier,
            'ref_id': uuid4(),
        }

        serialized_data = SubscriptionSerializer(data=stripe_data)
        is_valid = serialized_data.is_valid(raise_exception=True)

        if not is_valid:
            raise CustomException(
                'There was a problem recieving the IPN.',
                status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        saved_ipn = serialized_data.create(serialized_data.data)
        return saved_ipn

    def change_user_subscription(self, user, event, subscription):
        if event == 'customer.subscription.created' or event == 'customer.subscription.updated':
            if subscription == 'prod_MJKvTG7CmI8LA4':
                user.subscription_tier = 1
            elif subscription == 'prod_MJKvSCYjuoxCk2':
                user.subscription_tier = 2
            elif subscription == 'prod_MJKuG1zUSJtSCl':
                user.subscription_tier = 3

        if event == 'customer.subscription.deleted':
            user.subscription_tier = 0

        user.save()

    def check_subscription_limits(self, user):
        subscription = get_subscription(user_pk=user.pk)
        shops = Shop.objects.filter(owner=user)
        products = Product.objects.filter(shop=shops[0])

        if shops.count() > subscription['max_shops']:
            for index, shop in enumerate(shops):
                if 0 <= index <= subscription['max_shops'] - 1:
                    continue

                shop.status = 0
                shop.save()

        if products.count() > subscription['max_products']:
            for index, product in enumerate(products):
                if 0 <= index <= subscription['max_products'] - 1:
                    continue

                product.status = 0
                product.save()

    def get_user(self, user_ref):
        try:
            user = User.objects.get(ref_id=user_ref)
        except User.DoesNotExist:
            data = {
                'success': False,
                'message': 'A user could not be found.',
                'data': {}
            }

            return Response(data, status=status.HTTP_404_NOT_FOUND)

        return user

    def post(self, request):
        webhook_secret = os.environ['STRIPE_SUBSCRIPTION_WEBHOOK']

        if webhook_secret:
            signature = request.META.get('HTTP_STRIPE_SIGNATURE')

            try:
                event = stripe.Webhook.construct_event(
                    payload=request.body, sig_header=signature, secret=webhook_secret
                )

                event_data = event['data']

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
        else:
            event_data = request.data['data']
            event_type = request.data['type']

        if (event_type == 'customer.subscription.created' or
                event_type == 'customer.subscription.updated' or
                event_type == 'customer.subscription.deleted' or
                event_type == 'customer.subscription.pending_update_applied' or
                event_type == 'customer.subscription.pending_update_expired' and not
                event_data['object']['pending_update']):

            user = self.get_user(event_data['object']['metadata']['user_ref'])

            saved_ipn = self.save_webhook(
                user,
                event_data['object']['status'],
                event_data['object']['plan']['product'],
                event_data['object']
            )

            self.change_user_subscription(user, event_type, event_data['object']['plan']['product'])
            self.check_subscription_limits(user)

            data = {
                'success': True,
                'message': 'Webhook successfully recieved.',
                'data': {
                    'ref_id': saved_ipn.ref_id
                }
            }

            return Response(data, status=status.HTTP_200_OK)

        elif event_type == 'charge.succeeded':
            charge = stripe.Charge.retrieve(
                event_data['object']['id'],
                expand=['invoice.subscription']
            )

            user = self.get_user(charge['invoice']['subscription']['metadata']['user_ref'])

            stripe_data = {
                'user': user.pk,
                'provider': 1,
                'provider_data': event_data['object'],
                'status': 3,
                'ref_id': uuid4(),

            }

            context = {'request': request}
            serialized_data = SubscriptionPaymentSerializer(data=stripe_data, context=context)
            is_valid = serialized_data.is_valid(raise_exception=True)

            if not is_valid:
                raise CustomException(
                    'There was a problem recieving the IPN.',
                    status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            saved_ipn = serialized_data.create(serialized_data.data)

            data = {
                'success': True,
                'message': 'Webhook successfully recieved.',
                'data': {
                    'ref_id': saved_ipn.ref_id
                }
            }

            return Response(data, status=status.HTTP_200_OK)

        data = {
            'success': True,
            'message': 'Webhook successfully recieved.',
            'data': {}
        }

        return Response(data, status=status.HTTP_200_OK)
