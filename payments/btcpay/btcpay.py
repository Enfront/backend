from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

import os
import hmac
import hashlib
import btcpay

from payments.models import Payment, PaymentSession
from payments.serializers import PaymentSerializer, PaymentSessionSerializer
from payments.views import save_payment, save_payment_session, send_virtual_product_email
from products.views import change_stock
from orders.models import Order
from orders.serializers import OrderStatusSerializer
from shared.exceptions import CustomException


class PaymentCryptoView(APIView):
    permission_classes = [AllowAny]
    serializer_class = PaymentSessionSerializer

    def get(self, request, order_ref):
        if order_ref is None:
            raise CustomException(
                'An order id must be provided in the query params.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        try:
            order = Order.objects.get(ref_id=order_ref)
        except Order.DoesNotExist:
            raise CustomException(
                'An order with an id ' + str(order_ref) + ' could not be found.',
                status.HTTP_404_NOT_FOUND
            )

        crypto_payment = Payment.objects.filter(order=order, provider=2).last()

        if not crypto_payment:
            crypto_session = PaymentSession.objects.filter(order=order, provider=2).last()

            if not crypto_session:
                data = {
                    'success': False,
                    'message': 'A crypto session has not been found.',
                    'data': {},
                }

                return Response(data, status.HTTP_204_NO_CONTENT)

            payment_methods = btcpay.Invoices.get_invoice_payment_methods(crypto_session.provider_data['invoiceId'])
            payment_methods[0]['status'] = crypto_session.provider_data['type']

            data = {
                'success': True,
                'message': 'A crypto session has been found.',
                'data': payment_methods[0]
            }

            return Response(data, status.HTTP_200_OK)

        data = {
            'success': True,
            'message': 'A crypto payment has been found.',
            'data': {
                'status': crypto_payment.provider_data['type'],
            },
        }

        return Response(data, status.HTTP_200_OK)

    def post(self, request):
        order_data = request.data

        if order_data.get('order_ref') is None:
            raise CustomException(
                'An order id must be provided.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        elif order_data.get('fiat_currency') is None:
            raise CustomException(
                'The fiat currency must be provided.',
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
                'An order with an id ' + str(order_data['order_ref']) + ' could not be found.',
                status.HTTP_404_NOT_FOUND
            )

        invoice_data = {
            'amount': order.total / 100,
            'currency': order_data['fiat_currency'],
            'checkout': {
                'speedPolicy': 'MediumSpeed',
                'expirationMinutes': 60,
            },
            'metadata': {
                'email': order_data['email'],
                'orderId': str(order.ref_id),
            },
        }

        new_invoice = btcpay.Invoices.create_invoice(**invoice_data)
        payment_methods = btcpay.Invoices.get_invoice_payment_methods(new_invoice['id'])
        payment_methods[0]['status'] = new_invoice['status']

        data = {
            'success': True,
            'message': 'An invoice has been created.',
            'data': payment_methods[0],
        }

        return Response(data, status.HTTP_200_OK)


class PaymentCryptoIpnView(APIView):
    permission_classes = [AllowAny]

    def verify_webhook(self, request):
        webhook_secret = os.environ['BTC_WEBHOOK']
        signature = request.headers['Btcpay-Sig']

        my_signature = hmac.new(bytearray(webhook_secret, 'utf-8'), request.body, hashlib.sha256).hexdigest()
        my_signature_appended = 'sha256=' + my_signature

        if my_signature_appended != signature:
            return False

        return True

    def post(self, request):
        is_verified = self.verify_webhook(request)
        if not is_verified:
            data = {
                'success': False,
                'message': 'There was an error verifying the webhook signature.',
                'data': {}
            }

            return Response(data, status=status.HTTP_403_FORBIDDEN)

        webhook_data = request.data
        accepted_webhooks = (
            'InvoiceInvalid',
            'InvoiceExpired',
            'InvoiceCreated',
            'InvoiceReceivedPayment',
            'InvoiceProcessing',
            'InvoiceSettled',
        )

        if webhook_data['type'] in accepted_webhooks:
            instance = OrderStatusSerializer()

            invoice = btcpay.Invoices.get_invoice(webhook_data['invoiceId'])
            order = Order.objects.get(ref_id=invoice['metadata']['orderId'])

            match webhook_data['type']:
                case 'InvoiceInvalid':
                    save_payment(2, webhook_data, order, True)
                    OrderStatusSerializer.create(instance, {'order': order, 'status': -2})

                case 'InvoiceExpired':
                    save_payment(2, webhook_data, order, True)

                case 'InvoiceSettled':
                    OrderStatusSerializer.create(instance, {'order': order, 'status': 1})
                    OrderStatusSerializer.create(instance, {'order': order, 'status': 2})

                    save_payment(2, webhook_data, order, False)

                    for order_item in order.items.all():
                        change_stock(order_item.product_id, order_item.quantity, 'SUB')

                    send_virtual_product_email(invoice['metadata']['email'], order)

                    OrderStatusSerializer.create(instance, {'order': order, 'status': 3})

                case _:
                    save_payment_session(2, webhook_data, webhook_data['type'], order)

        data = {
            'success': True,
            'message': 'An IPN has been recieved.',
            'data': {},
        }

        return Response(data, status.HTTP_200_OK)
