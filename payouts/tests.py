from rest_framework.test import APITestCase
from rest_framework import status

from countries.models import Country
from shops.models import Shop
from users.models import User


class TestPayoutView(APITestCase):
    @classmethod
    def setUp(cls):
        cls.register_data = {
            'email': 'snow@castleblack.com',
            'username': 'YouKnowNothing',
            'first_name': 'John',
            'last_name': 'Snow',
            'password': 'ghost!123',
            'password_confirmation': 'ghost!123',
            'shop': True,
        }

        cls.login_data = {
            'email': 'snow@castleblack.com',
            'password': 'ghost!123',
            'shop': True
        }

        cls.country_data = {
            'num_code': 122,
            'iso_2': 'US',
            'iso_3': 'USA',
            'name': 'United States',
            'continent': 'North America',
            'stripe_available': True,
            'paypal_available': True
        }

    def create_user(self):
        user = User.objects.create_user(**self.register_data)
        user.is_active = True
        user.save()

        return user

    def create_shop(self):
        country = Country.objects.create(**self.country_data)
        user = self.create_user()

        shop_data = {
            'name': 'The Wall',
            'email': 'snow@castleblack.com',
            'owner': user,
            'country': country
        }

        shop = Shop.objects.create(**shop_data)
        return shop

    def test_get_payout_passing(self):
        shop = self.create_shop()

        self.client.post('/api/v1/users/login', self.login_data, secure=True)
        response = self.client.get('/api/v1/payouts/' + str(shop.ref_id), secure=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue('minimum' in response.data['data'])
