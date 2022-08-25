from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password

from users.models import User
from customers.models import Customer
from shops.models import Shop


class CustomAuthentication(BaseBackend):
    def authenticate(self, request, email=None, password=None, shop_name=None):
        try:
            if shop_name:
                shop = Shop.objects.get(name=shop_name)
                user = User.objects.get(email=email, customer__shop=shop)
            else:
                user = User.objects.get(email=email)

        except User.DoesNotExist:
            return None

        if not user.is_active:
            return None

        if not user.check_password(password):
            return None

        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
