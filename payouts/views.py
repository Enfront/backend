from django.db.models import Q

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

import btcpay

from .models import Payout
from .serializers import PayoutSerializer, PublicPayoutSerializer

from payments.models import PaymentProvider
from payments.serializers import PublicCryptoAddressSerializer
from shared.pagination import PaginationMixin, CustomPagination


class PayoutView(APIView, PaginationMixin):
    serializer_class = PayoutSerializer
    pagination_class = CustomPagination

    def get_payout_status_code(self, payout_status):
        match payout_status:
            case 'Cancelled':
                status_code = -1
            case 'AwaitingApproval':
                status_code = 0
            case 'AwaitingPayment' | 'InProgress':
                status_code = 1
            case 'Completed':
                status_code = 2
            case _:
                status_code = -1

        return status_code

    def check_pending_payouts(self, shop_ref):
        pending_payouts = Payout.objects.filter(Q(status=0) | Q(status=1), shop__ref_id=shop_ref)

        if pending_payouts.exists():
            for payout in pending_payouts:
                btcpay_payout_data = btcpay.PullPayments.get_pull_payment_payout(
                    payout.provider_data['pull_payment']['id'],
                    payout.provider_data['payout']['id']
                )

                payout.status = self.get_payout_status_code(btcpay_payout_data['state'])
                payout.save()

    def get(self, request, shop_ref):
        payout_return_data = {}

        self.check_pending_payouts(shop_ref)

        payouts = Payout.objects.filter(shop__ref_id=shop_ref).order_by('-created_at')
        if payouts.exists():
            page = self.paginate_queryset(payouts)
            payouts_data = PublicPayoutSerializer(page, many=True).data
            payouts_paginated = self.get_paginated_response(payouts_data).data
            payout_return_data['history'] = payouts_paginated

        crypto_addresses = PaymentProvider.objects.filter(shop__ref_id=shop_ref, provider=2, status=1).last()
        if crypto_addresses:
            crypto_addresses_data = PublicCryptoAddressSerializer(crypto_addresses).data

            payout_return_data['balance'] = crypto_addresses_data['balance']
            payout_return_data['bitcoin_address'] = crypto_addresses_data['provider_data']['bitcoin_address']

        data = {
            'success': True,
            'message': 'Payout information has been retrieved.',
            'data': payout_return_data,
        }

        return Response(data, status=status.HTTP_200_OK)
