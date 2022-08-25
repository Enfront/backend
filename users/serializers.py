from django.http import HttpResponseRedirect

from rest_framework import status
from rest_framework import serializers

from .models import User

from shared.exceptions import CustomException
from shared.services import create_form_errors, get_url
from customers.models import Customer
from shops.models import Shop


class UserSerializer(serializers.ModelSerializer):
    def partial_update(self, instance, validated_data):
        instance.email = validated_data['email']
        instance.username = validated_data['username']
        instance.last_name = validated_data['last_name']
        instance.first_name = validated_data['first_name']
        instance.save()

        return instance

    class Meta:
        model = User
        fields = ['email', 'username', 'first_name', 'last_name']


class RegisterUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password_confirmation = serializers.CharField(write_only=True)

    def create(self, validated_data, shop_name=None):
        shop = None
        anonymous_user = None

        if shop_name is not None:
            shop = Shop.objects.get(name=shop_name)

            try:
                anonymous_user = User.objects.get(email=validated_data['email'], customer__shop=shop)

                if anonymous_user.password and anonymous_user.has_usable_password():
                    create_form_errors(
                        'form',
                        'A user with this email already exists.',
                        status.HTTP_409_CONFLICT
                    )

                    return None
            except User.DoesNotExist:
                anonymous_user = None
        else:
            user_exists = User.objects.filter(email=validated_data['email'], customer__shop=None).exists()

            if user_exists:
                raise CustomException(
                    'A user with this email already exists.',
                    status.HTTP_409_CONFLICT,
                )

        custom_user = User.objects.create_user(**validated_data, customer=anonymous_user)

        if shop_name is not None and shop is not None and anonymous_user is None:
            Customer.objects.create(user=custom_user, shop=shop)

        return custom_user

    def validate_password(self, password):
        shop_name = self.context.get('request').data.get('shop_name')
        password_confirmation = self.context.get('request').data.get('password_confirmation')
        special_characters = "[~\!@#\$%\^&\*\(\)_\+{}\":;'\[\]]"

        if password != password_confirmation:
            if shop_name:
                create_form_errors(
                    'form',
                    'Password and password confirmation do not match.',
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                )

                return False

            raise CustomException(
                'Password and password confirmation do not match.',
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        if not any(char.isalpha() for char in password):
            if shop_name:
                create_form_errors(
                    'password',
                    'Password must contain a letter.',
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                )

                return False

            raise CustomException(
                'Password must contain a letter.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        if not any(char.isdigit() for char in password):
            if shop_name:
                create_form_errors(
                    'password',
                    'Password must contain a digit.',
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                )

                return False

            raise CustomException(
                'Password must contain a digit.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        if not any(char in special_characters for char in password):
            if shop_name:
                create_form_errors(
                    'password',
                    'Password must contain a special character.',
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                )

                return False

            raise CustomException(
                'Password must contain a special character.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        return password

    class Meta:
        model = User
        fields = '__all__'


class ResetPasswordSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password_confirmation = serializers.CharField(write_only=True)

    def validate_password(self, password):
        shop_name = self.context.get('request').data.get('shop_name')
        password_confirmation = self.context.get('request').data.get('password_confirmation')
        special_characters = "[~\!@#\$%\^&\*\(\)_\+{}\":;'\[\]]"

        if password != password_confirmation:
            if shop_name:
                create_form_errors(
                    'form',
                    'Password and password confirmation do not match.',
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                )

                return False

            raise CustomException(
                'Password and password confirmation do not match.',
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        if not any(char.isalpha() for char in password):
            if shop_name:
                create_form_errors(
                    'password',
                    'Password must contain a letter.',
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                )

                return False

            raise CustomException(
                'Password must contain a letter.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        if not any(char.isdigit() for char in password):
            if shop_name:
                create_form_errors(
                    'password',
                    'Password must contain a digit.',
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                )

                return False

            raise CustomException(
                'Password must contain a digit.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        if not any(char in special_characters for char in password):
            if shop_name:
                create_form_errors(
                    'password',
                    'Password must contain a special character.',
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                )

                return False

            raise CustomException(
                'Password must contain a special character.',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        return password

    class Meta:
        model = User
        fields = ['password', 'password_confirmation']


class PublicUserInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['ref_id', 'email', 'username', 'first_name', 'last_name', 'subscription_tier', 'is_active',
                  'created_at']
