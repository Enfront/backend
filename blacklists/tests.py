from rest_framework import status
from rest_framework.test import APITestCase

from blacklists.models import Blacklist
from countries.models import Country
from customers.models import Customer
from shops.models import Shop
from users.models import User


class TestBlacklistView(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.login_data = {
            'email': 'snow@castleblack.com',
            'password': 'ghost!123',
            'recaptcha': 'test',
            'shop': True
        }

        user = User.objects.create_user(**{
            'email': 'snow@castleblack.com',
            'username': 'YouKnowNothing',
            'first_name': 'John',
            'last_name': 'Snow',
            'password': 'ghost!123',
            'password_confirmation': 'ghost!123',
            'shop': True,
        })
        user.is_active = True
        user.save()

        cls.user = user

        country_data = {
            'num_code': 122,
            'iso_2': 'US',
            'iso_3': 'USA',
            'name': 'United States',
            'continent': 'North America',
            'stripe_available': True,
            'paypal_available': True
        }

        country = Country.objects.create(**country_data)
        cls.country = country

        shop = Shop.objects.create(**{
            'name': 'The Wall',
            'domain': 'https://castleblack.com',
            'email': 'snow@castleblack.com',
            'description': 'We sell harvested white walker souls.',
            'currency': 'USD',
            'country': country,
            'owner_id': user.id
        })

        cls.shop = shop

        customer = User.objects.create_user(**{
            'email': 'snow@castleblack.com',
            'username': 'YouKnowNothing',
            'first_name': 'John',
            'last_name': 'Snow',
            'password': 'ghost!123',
            'password_confirmation': 'ghost!123',
        })

        customer = Customer.objects.create(user=customer, shop=shop)
        cls.customer = customer

    def test_create_blacklist_item(self):
        blacklist_data = {
            'user': self.user.ref_id,
            'paypal_email': self.user.email,
            'country': 'Asshai',
            'ip_address': '192.168.1.1',
            'shop': self.shop.ref_id,
            'note': 'White walker ban.',
        }

        self.client.post('/api/v1/users/login', self.login_data, secure=True)
        response = self.client.post('/api/v1/blacklists', blacklist_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        blacklist_count = Blacklist.objects.count()
        self.assertEqual(blacklist_count, 1)

    def test_create_blacklist_bad_data(self):
        blacklist_data = {
            'ip_address': '',
            'shop': self.shop.ref_id,
            'note': 'White walker ban.',
        }

        self.client.post('/api/v1/users/login', self.login_data, secure=True)
        response = self.client.post('/api/v1/blacklists', blacklist_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        blacklist_count = Blacklist.objects.count()
        self.assertEqual(blacklist_count, 0)

    def test_delete_blacklist_item(self):
        blacklist_data = {
            'user': self.user.ref_id,
            'shop': self.shop.ref_id,
            'note': 'White walker ban.',
        }

        self.client.post('/api/v1/users/login', self.login_data, secure=True)
        response = self.client.post('/api/v1/blacklists', blacklist_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        blacklist_count = Blacklist.objects.count()
        self.assertEqual(blacklist_count, 1)

        response = self.client.delete(
            '/api/v1/blacklists/delete/{}'.format(response.data['data']['ref_id']),
            secure=True
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_get_blacklist_items(self):
        blacklist_data = {
            'user': self.user.ref_id,
            'shop': self.shop.ref_id,
            'note': 'White walker ban.',
        }

        self.client.post('/api/v1/users/login', self.login_data, secure=True)
        response = self.client.post('/api/v1/blacklists', blacklist_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        blacklist_count = Blacklist.objects.count()
        self.assertEqual(blacklist_count, 1)

        response = self.client.get('/api/v1/blacklists/{}'.format(self.shop.ref_id), secure=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_blacklist_items_bad_data(self):
        self.client.post('/api/v1/users/login', self.login_data, secure=True)
        response = self.client.get('/api/v1/blacklists/{}'.format(self.shop.ref_id), secure=True)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_blacklist_bad_ref(self):
        blacklist_data = {
            'user': self.user.ref_id,
            'shop': self.shop.ref_id,
            'note': 'White walker ban.',
        }

        self.client.post('/api/v1/users/login', self.login_data, secure=True)
        response = self.client.post('/api/v1/blacklists', blacklist_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        blacklist_count = Blacklist.objects.count()
        self.assertEqual(blacklist_count, 1)

        response = self.client.delete(
            '/api/v1/blacklists/delete/{}'.format('84e8c5d7-5b05-4532-a9b8-3eb7f5f7b6cc'),
            secure=True
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
