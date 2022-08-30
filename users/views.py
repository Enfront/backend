from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.template.loader import render_to_string
from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import rotate_token, get_token
from django.http import HttpResponseRedirect
from django.conf import settings

from rest_framework.authentication import SessionAuthentication
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from captcha.fields import ReCaptchaField
from captcha.widgets import ReCaptchaV3

import os

from .serializers import RegisterUserSerializer, PublicUserInfoSerializer, UserSerializer, ResetPasswordSerializer
from .models import User
from .tokens import account_activation_token, forgot_password_token

from shared.services import send_mailgun_email, create_form_errors, get_url
from shared.exceptions import CustomException

from shops.models import Shop
from customers.models import Customer


class UserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.pk:
            raise CustomException(
                'A user with id ' + request.user.pk + ' was not found.',
                status.HTTP_404_NOT_FOUND,
            )

        user = PublicUserInfoSerializer(request.user).data

        data = {
            'success': True,
            'message': 'A user was found.',
            'data': user
        }

        return Response(data, status=status.HTTP_200_OK)

    def patch(self, request):
        if not request.user.pk:
            raise CustomException(
                'A user with id ' + request.user.pk + ' was not found.',
                status.HTTP_404_NOT_FOUND,
            )

        serialized_data = UserSerializer(request.user, data=request.data, partial=True)
        is_valid = serialized_data.is_valid(raise_exception=True)

        if not is_valid:
            raise CustomException(
                'There was a problem saving the user data.',
                status.HTTP_400_BAD_REQUEST
            )

        serialized_data.save()

        data = {
            'success': True,
            'message': 'The user data was successfully saved.',
            'data': {}
        }

        return Response(data, status=status.HTTP_200_OK)


class RegisterUserView(APIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterUserSerializer

    def send_activation_email(self, user, shop_name):
        token = account_activation_token.make_token(user)
        activation_link = mark_safe(
            os.environ['SITE_SCHEME'] +
            os.environ['SITE_URL']
            + '/api/v1/users/activate?ref_id='
            + str(user.ref_id)
            + '&token='
            + token
            + ('&shop=' + shop_name if shop_name is not None else '')
        )

        context = {
            'activation_link': activation_link,
            'full_name': user.first_name + ' ' + user.last_name
        }

        email_subject = 'Activate Your Account'
        email_body = render_to_string(
            os.path.join(settings.BASE_DIR, 'templates', 'emails', 'account_activation.jinja2'),
            context
        )

        send_mailgun_email(user.email, email_subject, email_body, 'auth')

    def post(self, request):
        register_data = request.data

        context = {'request': request}
        serialized_data = self.serializer_class(data=register_data, context=context)
        is_valid = serialized_data.is_valid(raise_exception=False)

        captcha_valid = ReCaptchaField(widget=ReCaptchaV3)
        if not is_valid or not captcha_valid:
            if register_data.get('shop') is None and register_data.get('shop_name') is not None:
                for key, values in serialized_data.errors.items():
                    create_form_errors(
                        key,
                        [value[:] for value in values][0],
                        status.HTTP_400_BAD_REQUEST
                    )

                return HttpResponseRedirect(get_url('/register', register_data.get('shop_name')))

            data = {
                'success': False,
                'message': 'Recaptcha failed.',
                'data': {},
            }

            return Response(data, status.HTTP_401_UNAUTHORIZED)

        user_info = serialized_data.create(serialized_data.validated_data, register_data.get('shop_name'))

        if user_info is None:
            return HttpResponseRedirect(get_url('/register', register_data.get('shop_name')))

        self.send_activation_email(user_info, register_data.get('shop_name'))

        if register_data.get('shop') is None and register_data.get('shop_name') is not None:
            return HttpResponseRedirect(get_url('/activate', register_data.get('shop_name')))

        data = {
            'success': True,
            'message': 'A user was successfully registered.',
            'data': {
                'ref_id': user_info.ref_id,
                'email': user_info.email,
            },
        }

        return Response(data, status.HTTP_201_CREATED)


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def send_forgot_email(self, user, shop_name):
        token = forgot_password_token.make_token(user)
        forgot_password_link = mark_safe(
            os.environ['SITE_SCHEME']
            + (slugify(shop_name) + '.' if shop_name is not None else '')
            + os.environ['SITE_URL']
            + '/reset?ref_id='
            + str(user.ref_id)
            + '&token='
            + token
        )

        context = {
            'forgot_password_link': forgot_password_link,
        }

        email_subject = 'Reset Your Password'
        email_body = render_to_string(
            os.path.join(settings.BASE_DIR, 'templates', 'emails', 'reset_password.jinja2'),
            context
        )

        send_mailgun_email(user.email, email_subject, email_body, 'auth')

    def post(self, request):
        forgot_data = request.data

        if forgot_data.get('email') is None:
            if forgot_data.get('shop') is None:
                create_form_errors(
                    'form',
                    'Email must be provided.',
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                )

            raise CustomException(
                'Email must be provided.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        captcha_valid = ReCaptchaField(widget=ReCaptchaV3)
        if not captcha_valid:
            if forgot_data.get('shop') is None:
                create_form_errors(
                    'form',
                    'Recaptcha failed.',
                    status.HTTP_401_UNAUTHORIZED
                )

            data = {
                'success': False,
                'message': 'Recaptcha failed.',
                'data': {},
            }

            return Response(data, status.HTTP_401_UNAUTHORIZED)

        try:
            user_info = User.objects.get(email=forgot_data.get('email'))
        except User.DoesNotExist:
            if forgot_data.get('shop') is None:
                create_form_errors(
                    'form',
                    'A user with email ' + forgot_data.get('email') + ' does not exist.',
                    status.HTTP_404_NOT_FOUND
                )

                return HttpResponseRedirect(get_url('/forgot', forgot_data.get('shop_name')))

            raise CustomException(
                'A user with email ' + forgot_data.get('email') + ' does not exist.',
                status.HTTP_404_NOT_FOUND
            )

        self.send_forgot_email(user_info, forgot_data.get('shop_name'))

        if forgot_data.get('shop') is None:
            return HttpResponseRedirect(get_url('/', forgot_data.get('shop_name')))

        data = {
            'success': True,
            'message': 'Reset password email successfully sent.',
            'data': {},
        }

        return Response(data, status.HTTP_200_OK)


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]
    serializer_class = ResetPasswordSerializer

    def post(self, request):
        reset_data = request.data

        user_ref = reset_data.get('ref_id')
        token = reset_data.get('token')
        shop_name = reset_data.get('shop_name')

        try:
            user_info = User.objects.get(user_ref=user_ref)
        except User.DoesNotExist:
            if reset_data.get('shop') is None:
                create_form_errors(
                    'form',
                    'A user with the ref id ' + user_ref + ' does not exist.',
                    status.HTTP_404_NOT_FOUND
                )

                return HttpResponseRedirect(get_url('/forgot', shop_name))

            raise CustomException(
                'A user with the ref id ' + user_ref + ' does not exist.',
                status.HTTP_404_NOT_FOUND
            )

        context = {'request': request}
        serialized_data = self.serializer_class(data=reset_data, context=context)
        is_valid = serialized_data.is_valid(raise_exception=True)

        if not is_valid:
            if reset_data.get('shop') is None:
                create_form_errors(
                    'form',
                    'There was a problem changing your password.',
                    status.HTTP_400_BAD_REQUEST
                )

                return HttpResponseRedirect(get_url('/forgot', shop_name))

            raise CustomException(
                'There was a problem changing your password.',
                status.HTTP_400_BAD_REQUEST
            )

        if not forgot_password_token.check_token(user_info, token):
            if reset_data.get('shop') is None:
                create_form_errors(
                    'form',
                    'The reset token is not valid.',
                    status.HTTP_401_UNAUTHORIZED
                )

                return HttpResponseRedirect(get_url('/forgot', shop_name))

            raise CustomException(
                'The reset token is not valid',
                status.HTTP_401_UNAUTHORIZED
            )

        user_info.set_password(reset_data.get('password'))
        user_info.save()

        if shop_name is not None:
            return HttpResponseRedirect(get_url('/', shop_name))

        return HttpResponseRedirect(get_url('/'))


class ActivateUserView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        user_ref = request.GET['ref_id']
        token = request.GET['token']
        shop_name = None

        if 'shop' in request.GET:
            shop_name = request.GET['shop']

        try:
            user_info = User.objects.get(ref_id=user_ref)
        except User.DoesNotExist:
            raise CustomException(
                'A user with the ref id ' + user_ref + ' does not exist.',
                status.HTTP_404_NOT_FOUND
            )

        if account_activation_token.check_token(user_info, token):
            user_info.is_active = True
            user_info.save()

        if shop_name is not None:
            return HttpResponseRedirect(get_url('/', shop_name))

        return HttpResponseRedirect(get_url('/'))


class LoginUserView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]

    def post(self, request):
        auth_data = request.data

        if auth_data.get('shop') is None and auth_data.get('shop_name') is None:
            raise CustomException(
                'Shop name must be provided.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        user = authenticate(
            email=auth_data.get('email'),
            password=auth_data.get('password'),
            shop_name=auth_data.get('shop_name')
        )

        if user is None:
            if auth_data.get('shop'):
                raise CustomException(
                    'Email and/or password is incorrect.',
                    status.HTTP_401_UNAUTHORIZED
                )

            create_form_errors(
                'form',
                'Email and/or password is incorrect.',
                status.HTTP_401_UNAUTHORIZED
            )

            return HttpResponseRedirect(get_url('/login', auth_data.get('shop_name')))

        captcha_valid = ReCaptchaField(widget=ReCaptchaV3)
        if not captcha_valid:
            if auth_data.get('shop'):
                data = {
                    'success': false,
                    'message': 'Recaptcha failed.',
                    'data': {},
                }

                return Response(data, status=status.HTTP_401_UNAUTHORIZED)

            create_form_errors(
                'form',
                'Recaptcha failed.',
                status.HTTP_401_UNAUTHORIZED
            )

            return HttpResponseRedirect(get_url('/login', auth_data.get('shop_name')))

        login(request, user)

        if auth_data.get('shop') is None:
            response = HttpResponseRedirect(get_url('/', auth_data.get('shop_name')))
            response.set_cookie('_enfront_uid', user.ref_id, 604800)

            return response

        data = {
            'success': True,
            'message': 'Login successful.',
            'data': {},
        }

        response = Response(data, status=status.HTTP_200_OK)

        return response


class LogoutUserView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        auth_data = request.data

        if auth_data.get('shop') is None and auth_data.get('shop_name') is None:
            raise CustomException(
                'Shop name must be provided.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        logout(request)

        if auth_data.get('shop') is None:
            return HttpResponseRedirect(get_url('/', auth_data.get('shop_name')))

        data = {
            'success': True,
            'message': 'Logout successful.',
            'data': {},
        }

        return Response(data, status=status.HTTP_200_OK)


class GetCsrfTokenView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        data = {
            'success': True,
            'message': 'Token successfully retrieved.',
            'data': {}
        }

        response = Response(data, status=status.HTTP_200_OK)
        response['X-CSRFToken'] = get_token(request)
        return response


class CheckAuthStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_authenticated:
            data = {
                'success': False,
                'message': 'A session does not exist.',
                'data': {},
            }

            return Response(data, status=status.HTTP_401_UNAUTHORIZED)

        data = {
            'success': True,
            'message': 'There is an active session.',
            'data': {}
        }

        return Response(data, status=status.HTTP_200_OK)
