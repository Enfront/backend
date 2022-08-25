from django.utils.encoding import force_str

from rest_framework import status
from rest_framework.exceptions import APIException


class CustomException(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = 'A server error has occurred.'

    def __init__(self, detail, status_code):
        if status_code is not None:
            self.status_code = status_code

        if detail is not None:
            self.detail = {
                'success': False,
                'message': force_str(detail),
                'response:': {},
            }
        else:
            self.detail = {'detail': force_str(self.default_detail)}
