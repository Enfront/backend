from django.utils.text import slugify
from rest_framework import status

import datetime
import requests
import decimal
import math
import os

from users.models import User
from shops.models import Shop
from orders.models import Order
from payments.models import Payment
from shared.exceptions import CustomException


def get_subscription(user_pk=None, user_ref=None, shop_ref=None):
    subscription = {}
    subscription_tier = 0

    if user_ref is not None:
        try:
            owner = User.objects.get(ref_id=user_ref)
            subscription_tier = owner.subscription_tier
        except User.DoesNotExist:
            raise CustomException(
                'A user with id ' + str(user_ref) + ' does not exist.',
                status.HTTP_404_NOT_FOUND
            )
    elif user_pk is not None:
        try:
            owner = User.objects.get(pk=user_pk)
            subscription_tier = owner.subscription_tier
        except User.DoesNotExist:
            raise CustomException(
                'A user with id ' + str(user_pk) + ' does not exist.',
                status.HTTP_404_NOT_FOUND
            )
    elif shop_ref is not None:
        try:
            owner = Shop.objects.get(ref_id=shop_ref)
            subscription_tier = owner.owner.subscription_tier
        except Shop.DoesNotExist:
            raise CustomException(
                'A shop with id ' + str(shop_ref) + ' does not exist.',
                status.HTTP_404_NOT_FOUND
            )

    if subscription_tier == 3:
        subscription['tier'] = 3
        subscription['max_products'] = 99999
        subscription['max_shops'] = 99999
        subscription['fee'] = decimal.Decimal(0.005)
    elif subscription_tier == 2:
        subscription['tier'] = 2
        subscription['max_shops'] = 5
        subscription['max_products'] = 99999
        subscription['fee'] = decimal.Decimal(0.01)
    elif subscription_tier == 1:
        subscription['tier'] = 1
        subscription['max_shops'] = 3
        subscription['max_products'] = 99999
        subscription['fee'] = decimal.Decimal(0.02)
    else:
        subscription['tier'] = 0
        subscription['max_shops'] = 1
        subscription['max_products'] = 99999
        subscription['fee'] = decimal.Decimal(0.03)

    return subscription


def get_total_fees(shop_ref):
    today = datetime.date.today()
    orders = Order.objects.filter(
        shop__ref_id=shop_ref,
        created_at__year=today.year,
        created_at__month=today.month
    )

    total_fees = decimal.Decimal(0.0)
    for order in orders:
        if order.current_status >= 1:
            try:
                payment = Payment.objects.get(order=order, canceled_at=None)
                total_fees += payment.fee
            except Payment.DoesNotExist:
                continue

    return total_fees


def get_order_fees(order_total, shop_ref, provider, round_up=True):
    try:
        shop = Shop.objects.get(ref_id=shop_ref)
    except Shop.DoesNotExist:
        raise CustomException(
            'A shop with id ' + str(shop_ref) + ' does not exist.',
            status.HTTP_404_NOT_FOUND
        )

    # Take 0% fees for PayPal
    if provider == 0:
        return 0

    # In line with Brazilian regulatory and compliance requirements, platforms based outside of
    # Brazil, with Brazilian connected accounts cannot collect application fees through Stripe.
    if provider == 1 and shop.country.num_code == 76:
        return 0

    fee_percentage = get_subscription(shop_ref=shop_ref)

    # we don't want to round when dealing with crypto amounts
    if not round_up:
        return order_total * fee_percentage['fee']

    return math.ceil(order_total * fee_percentage['fee'])


def get_url(path, subpath=''):
    if subpath != '':
        return os.environ['SITE_SCHEME'] + slugify(subpath) + '.' + os.environ['SITE_URL'] + path

    return os.environ['SITE_SCHEME'] + os.environ['SITE_URL'] + path


def send_mailgun_email(recipient, subject, body, purpose):
    if purpose == 'auth':
        mg_secret = os.environ['MG_API_SECRET']
        email_address = 'Enfront <notice@enfront.io>'
        domain_name = 'mg.enfront.io'
    else:
        mg_secret = os.environ['MG_ORDER_API_SECRET']
        email_address = 'Enfront <notice@orders.enfront.io>'
        domain_name = 'orders.enfront.io'

    if os.environ['PAYPAL_ENVIRONMENT'] == 'LiveEnvironment':
        requests.post(
            'https://api.mailgun.net/v3/' + domain_name + '/messages',
            auth=('api', mg_secret),
            data={
                'from': email_address,
                'to': [recipient],
                'subject': subject,
                'html': body
            }
        )
    else:
        print(subject)


form_errors = {}


def create_form_errors(key, message, error_status):
    form_errors[key] = {'message': message, 'status': error_status}


def get_form_errors():
    return form_errors


def reset_form_errors():
    form_errors.clear()
