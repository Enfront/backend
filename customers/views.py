from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Customer, CustomerNote
from .serializers import (
    CustomerSerializer,
    CustomerNoteSerializer,
    PublicCustomerInfoSerializer,
    PublicCustomerExpandedSerializer,
    PublicCustomerNoteSerializer
)

from shared.pagination import PaginationMixin, CustomPagination
from shared.exceptions import CustomException
from users.models import User
from users.serializers import UserSerializer


class CustomerView(APIView, PaginationMixin):
    permission_classes = [IsAuthenticated]
    serializer_class = CustomerSerializer
    pagination_class = CustomPagination

    def check_for_existing_user(self, email, shop):
        return Customer.objects.filter(user__email=email, shop=shop).exists()

    def get(self, request, shop_ref=None, customer_ref=None):
        if shop_ref is not None and customer_ref is None:
            context = {'shop_ref': shop_ref}
            seach_query = request.query_params.get('q')

            if seach_query:
                customers = Customer.objects.filter(shop__ref_id=shop_ref, user__email__contains=seach_query)\
                    .order_by('-user__created_at')

                if not customers:
                    data = {
                        'success': False,
                        'message': 'Customer(s) that match your criteria were not found.',
                        'data': {
                            'results': []
                        },
                    }

                    return Response(data, status=status.HTTP_200_OK)
            else:
                customers = Customer.objects.filter(shop__ref_id=shop_ref).order_by('-user__created_at')

            page = self.paginate_queryset(customers)
            if page is not None:
                customers_page = PublicCustomerInfoSerializer(page, context=context, many=True).data
                customers_paginated = self.get_paginated_response(customers_page).data

                data = {
                    'success': True,
                    'message': 'Customers have been been found.',
                    "data": customers_paginated
                }

                return Response(data, status=status.HTTP_200_OK)

        if shop_ref is not None and customer_ref is not None:
            try:
                customer = Customer.objects.get(user__ref_id=customer_ref)
                customer_data = PublicCustomerExpandedSerializer(customer).data

                page = self.paginate_queryset(customer_data['orders'])
                if page is not None:
                    customer_data['orders'] = self.get_paginated_response(page).data

            except Customer.DoesNotExist:
                data = {
                    'success': False,
                    'message': 'A customer with ref id ' + str(customer_ref) + ' could not be found.',
                    "data": [],
                }

                return Response(data, status=status.HTTP_404_NOT_FOUND)

            data = {
                'success': True,
                'message': 'A customer with ref id ' + str(customer_ref) + ' has been been found.',
                "data": customer_data,
            }

            return Response(data, status=status.HTTP_200_OK)

        data = {
            'success': False,
            'message': 'A customer ref id and shop ref id must be provided.',
            "data": [],
        }

        return Response(data, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

    def patch(self, request):
        customer_data = request.data

        context = {'request': request}
        serialized_data = UserSerializer(data=customer_data, context=context, partial=True)
        is_valid = serialized_data.is_valid(raise_exception=True)

        if not is_valid:
            raise CustomException(
                'A customer with id ' + str(request['customer_ref']) + ' could not be updated.',
                status.HTTP_400_BAD_REQUEST
            )

        try:
            customer_to_update = User.objects.get(ref_id=customer_data.get('customer'))

            if customer_to_update.email != customer_data.get('email'):
                email_exists = self.check_for_existing_user(
                    customer_data.get('email'),
                    customer_to_update.customer.shop
                )

                if email_exists:
                    raise CustomException(
                        'A customer with the email ' + customer_data.get('email') + ' already exists.',
                        status.HTTP_409_CONFLICT
                    )

            customer = serialized_data.partial_update(customer_to_update, serialized_data.data)
        except Customer.DoesNotExist:
            raise CustomException(
                'A customer with id ' + str(customer_data.get('customer')) + ' was not found.',
                status.HTTP_404_NOT_FOUND,
                )

        data = {
            'success': True,
            'message': 'Customer ' + str(customer_data.get('customer')) + ' has been updated.',
            'data': {
                'ref_id': customer.ref_id,
            },
        }

        return Response(data, status=status.HTTP_200_OK)


class CustomerNotesView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CustomerNoteSerializer

    def get(self, request, customer_ref):
        if customer_ref is None:
            raise CustomException(
                'A customer ref id is required.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        notes = CustomerNote.objects.filter(customer__user__ref_id=customer_ref, status=0)

        if notes.count() == 0:
            data = {
                'success': False,
                'message': 'No notes for a customer with ref ID ' + str(customer_ref) + ' have been found.',
                "data": [],
            }

            return Response(data, status=status.HTTP_204_NO_CONTENT)

        note_data = PublicCustomerNoteSerializer(notes, many=True).data

        data = {
            'success': True,
            'message': 'Notes for a customer with ref ID ' + str(customer_ref) + ' have been found.',
            "data": note_data,
        }

        return Response(data, status=status.HTTP_200_OK)

    def post(self, request):
        note_data = request.data

        if note_data.get('note') is None:
            raise CustomException(
                'A note is required.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        elif note_data.get('customer') is None:
            raise CustomException(
                'A customer ref id is required.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        context = {'request': request}
        serialized_data = self.serializer_class(data=note_data, context=context)
        is_valid = serialized_data.is_valid(raise_exception=True)

        if not is_valid:
            data = {
                'success': False,
                'message': 'There was an issue creating a customer note.',
                'data': {}
            }

            return Response(data, status=status.HTTP_400_BAD_REQUEST)

        note = serialized_data.create(serialized_data.data)
        if not note:
            raise CustomException(
                'There was an issue creating a customer note.',
                status.HTTP_400_BAD_REQUEST
            )

        data = {
            'success': True,
            'message': 'A customer note has been created.',
            'data': {
                'ref_id': note.ref_id,
            },
        }

        return Response(data, status=status.HTTP_201_CREATED)

    def delete(self, request, note_ref):
        if note_ref is None:
            raise CustomException(
                'A note ref must be provided.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        try:
            note = CustomerNote.objects.get(ref_id=note_ref)
            note.status = -1
            note.save()
        except CustomerNote.DoesNotExist:
            raise CustomException(
                'There was an error deleting a customer note with id ' + str(note_ref) + '.',
                status.HTTP_400_BAD_REQUEST
            )

        data = {
            'success': True,
            'message': 'A customer note with ref id ' + str(note_ref) + ' was deleted.',
            'data': {},
        }

        return Response(data, status=status.HTTP_204_NO_CONTENT)
