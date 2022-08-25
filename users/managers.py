from django.contrib.auth.base_user import BaseUserManager

from rest_framework import status

from shared.exceptions import CustomException


class CustomUserManager(BaseUserManager):
    def create_user(self, **kwargs):
        if not kwargs.get('email'):
            raise CustomException(
                'Email must be included in the request.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        elif not kwargs.get('username'):
            raise CustomException(
                'Username must be included in the request.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        elif not kwargs.get('first_name'):
            raise CustomException(
                'First name must be included in the request.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        elif not kwargs.get('last_name'):
            raise CustomException(
                'Last name must be included in the request.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        email = self.normalize_email(kwargs.get('email'))

        user = kwargs.get('customer')
        if user is not None:
            user.username = kwargs.get('username')
            user.first_name = kwargs.get('first_name')
            user.last_name = kwargs.get('last_name')
        else:
            user = self.model(
                email=email,
                username=kwargs.get('username'),
                first_name=kwargs.get('first_name'),
                last_name=kwargs.get('last_name')
            )

        user.set_password(kwargs.get('password'))
        user.save()

        return user
