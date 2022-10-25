from rest_framework.test import APITestCase
from rest_framework import status

from countries.models import Country
from shops.models import Shop
from users.models import User
from themes.models import Theme, ThemeConfiguration


class TestShopView(APITestCase):
    @classmethod
    def setUpTestData(cls):
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

        theme_data = {
            'name': 'Winterfell',
            'developer': user
        }

        theme = Theme.objects.create(**theme_data)
        cls.theme = theme

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

        cls.shop_data = {
            'name': 'The Wall',
            'domain': 'https://castleblack.com',
            'email': 'snow@castleblack.com',
            'description': 'We sell harvested white walker souls.',
            'currency': 'USD',
            'country': country,
            'owner_id': user.id
        }

    def create_shop(self):
        shop = Shop.objects.create(**self.shop_data)
        configuration_data = {
            'shop': shop,
            'theme': self.theme,
            'file_name': 'test_file.json',
            'status': 1
        }

        ThemeConfiguration.objects.create(**configuration_data)
        return shop

    def test_get_shop_by_ref_id(self):
        shop = self.create_shop()

        self.client.post('/api/v1/users/login', self.login_data, secure=True)
        response = self.client.get('/api/v1/shops/' + str(shop.ref_id), secure=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data'], {
            'name': 'The Wall',
            'email': 'snow@castleblack.com',
            'status': 0,
            'currency': 'USD',
            'domain': 'https://castleblack.com',
            'country': {
                'id': self.country.id,
                'num_code': 122,
                'iso_2': 'US',
                'iso_3': 'USA',
                'name': 'United States',
                'continent': 'North America',
                'stripe_available': True,
                'paypal_available': True,
            },
            'current_theme': {
                'name': 'Winterfell',
                'description': None,
                'developer': 'YouKnowNothing',
                'updated_at': self.theme.updated_at.isoformat().replace('+00:00', 'Z'),
                'ref_id': str(self.theme.ref_id)
            },
            'owner': {
                'username': 'YouKnowNothing',
                'subscription_tier': 0
            },
            'ref_id': str(shop.ref_id)
        })

    def test_get_shop_by_ref_id_that_does_not_exist(self):
        self.client.post('/api/v1/users/login', self.login_data, secure=True)
        response = self.client.get('/api/v1/shops/84e8c5d7-5b05-4532-a9b8-3eb7f5f7b6cc', secure=True)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_shop_by_ref_id_omit_deleted(self):
        shop = self.create_shop()
        shop.status = -1
        shop.save()

        self.client.post('/api/v1/users/login', self.login_data, secure=True)
        response = self.client.get('/api/v1/shops/' + str(shop.ref_id), secure=True)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_all_shops(self):
        shop = self.create_shop()

        self.client.post('/api/v1/users/login', self.login_data, secure=True)
        response = self.client.get('/api/v1/shops', secure=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(isinstance(response.data['data'], list))
        self.assertEqual(response.data['data'], [{
            'name': 'The Wall',
            'email': 'snow@castleblack.com',
            'status': 0,
            'currency': 'USD',
            'domain': 'https://castleblack.com',
            'country': {
                'id': self.country.id,
                'num_code': 122,
                'iso_2': 'US',
                'iso_3': 'USA',
                'name': 'United States',
                'continent': 'North America',
                'stripe_available': True,
                'paypal_available': True,
            },
            'current_theme': {
                'name': 'Winterfell',
                'description': None,
                'developer': 'YouKnowNothing',
                'updated_at': self.theme.updated_at.isoformat().replace('+00:00', 'Z'),
                'ref_id': str(self.theme.ref_id)
            },
            'owner': {
                'username': 'YouKnowNothing',
                'subscription_tier': 0
            },
            'ref_id': str(shop.ref_id)
        }])

    def test_get_all_shops_omit_deleted(self):
        shop = self.create_shop()
        shop.status = -1
        shop.save()

        self.client.post('/api/v1/users/login', self.login_data, secure=True)
        response = self.client.get('/api/v1/shops', secure=True)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_get_all_shops_only_by_user(self):
        shop = self.create_shop()
        user = User.objects.create_user(**{
            'email': 'imposter@castleblack.com',
            'username': 'IKnowEverything',
            'first_name': 'Don',
            'last_name': 'Melt',
            'password': 'zombie!123',
            'password_confirmation': 'zombie!123',
            'shop': True,
        })

        user.is_active = True
        user.save()

        shop.owner = user
        shop.save()

        self.client.post('/api/v1/users/login', self.login_data, secure=True)
        response = self.client.get('/api/v1/shops', secure=True)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_create_shop(self):
        self.shop_data['country'] = 1

        self.client.post('/api/v1/users/login', self.login_data, secure=True)
        response = self.client.post('/api/v1/shops', self.shop_data, secure=True)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_shop_with_no_email(self):
        # noinspection PyTypedDict
        self.shop_data['email'] = None
        self.shop_data['country'] = 1

        self.client.post('/api/v1/users/login', self.login_data, secure=True)
        response = self.client.post('/api/v1/shops', self.shop_data, secure=True)

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

        shop_count = Shop.objects.count()
        self.assertEqual(shop_count, 0)

    def test_create_shop_with_no_name(self):
        # noinspection PyTypedDict
        self.shop_data['name'] = None
        self.shop_data['country'] = 1

        self.client.post('/api/v1/users/login', self.login_data, secure=True)
        response = self.client.post('/api/v1/shops', self.shop_data, secure=True)

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

        shop_count = Shop.objects.count()
        self.assertEqual(shop_count, 0)

    def test_create_shop_with_duplicate_domain(self):
        self.create_shop()

        self.shop_data['country'] = 1
        self.shop_data['name'] = 'Kings Landing'

        self.client.post('/api/v1/users/login', self.login_data, secure=True)
        response = self.client.post('/api/v1/shops', self.shop_data, secure=True)

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

        shop_count = Shop.objects.count()
        self.assertEqual(shop_count, 1)

    def test_create_shop_and_exceed_limit(self):
        self.create_shop()

        self.shop_data['country'] = 1
        self.shop_data['name'] = 'Kings Landing'
        self.shop_data['domain'] = 'https://kingslanding.gov'

        self.client.post('/api/v1/users/login', self.login_data, secure=True)
        response = self.client.post('/api/v1/shops', self.shop_data, secure=True)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        shop_count = Shop.objects.count()
        self.assertEqual(shop_count, 1)

    def test_create_multiple_shops(self):
        self.create_shop()

        user = User.objects.get(id=1)
        user.subscription_tier = 3
        user.save()

        self.shop_data['country'] = 1
        self.shop_data['name'] = 'Kings Landing'
        self.shop_data['domain'] = 'https://kingslanding.gov'

        self.client.post('/api/v1/users/login', self.login_data, secure=True)
        response = self.client.post('/api/v1/shops', self.shop_data, secure=True)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        shop_count = Shop.objects.count()
        self.assertEqual(shop_count, 2)

    def test_edit_shop_details(self):
        shop = self.create_shop()

        self.client.post('/api/v1/users/login', self.login_data, secure=True)

        edited_shop_details = {
            'name': 'The Failed Wall',
            'domain': 'https://castleblack.gov',
            'email': 'snow@castleblack.gov',
            'status': 0
        }

        response = self.client.put('/api/v1/shops/' + str(shop.ref_id), edited_shop_details, secure=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        edited_shop = Shop.objects.get(id=shop.id)
        self.assertEqual(edited_shop.name, 'The Failed Wall')
        self.assertEqual(edited_shop.domain, 'https://castleblack.gov')
        self.assertEqual(edited_shop.email, 'snow@castleblack.gov')
        self.assertEqual(edited_shop.status, 0)

    def test_edit_shop_details_with_no_ref_id(self):
        shop = self.create_shop()

        self.client.post('/api/v1/users/login', self.login_data, secure=True)

        edited_shop_details = {
            'name': 'The Failed Wall',
            'domain': 'https://castleblack.com',
            'email': 'snow@castleblack.com',
            'status': 1
        }

        response = self.client.put('/api/v1/shops', edited_shop_details, secure=True)
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(Shop.objects.get(id=shop.id).name, 'The Wall')

    def test_edit_shop_with_ref_id_that_does_not_exist(self):
        shop = self.create_shop()

        self.client.post('/api/v1/users/login', self.login_data, secure=True)

        edited_shop_details = {
            'name': 'The Failed Wall',
            'domain': 'https://castleblack.com',
            'email': 'snow@castleblack.com',
            'status': 1
        }

        response = self.client.put(
            '/api/v1/shops/84e8c5d7-5b05-4532-a9b8-3eb7f5f7b6cc',
            edited_shop_details,
            secure=True
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(Shop.objects.get(id=shop.id).name, 'The Wall')

    def test_edit_shop_details_with_duplicate_domain(self):
        self.create_shop()

        self.shop_data['name'] = 'Kings Landing'
        self.shop_data['email'] = 'theroyals@haha.com'
        self.shop_data['domain'] = 'https://kingslanding.gov'

        shop = self.create_shop()

        edited_shop_details = {
            'name': 'Kings Landing',
            'domain': 'https://castleblack.com',
            'email': 'theroyals@haha.com',
            'status': 1
        }

        self.client.post('/api/v1/users/login', self.login_data, secure=True)
        response = self.client.put('/api/v1/shops/' + str(shop.ref_id), edited_shop_details, secure=True)

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(Shop.objects.get(id=shop.id).domain, 'https://kingslanding.gov')

    def test_delete_shop(self):
        shop = self.create_shop()

        self.client.post('/api/v1/users/login', self.login_data, secure=True)

        shop_count = Shop.objects.count()
        self.assertEqual(shop_count, 1)

        response = self.client.delete('/api/v1/shops/' + str(shop.ref_id), secure=True)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Shop.objects.get(id=shop.id).status, -1)

    def test_delete_shop_with_no_ref_id(self):
        self.create_shop()

        self.client.post('/api/v1/users/login', self.login_data, secure=True)

        shop_count = Shop.objects.count()
        self.assertEqual(shop_count, 1)

        response = self.client.delete('/api/v1/shops', secure=True)
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_delete_shop_with_ref_id_that_does_not_exist(self):
        self.create_shop()

        self.client.post('/api/v1/users/login', self.login_data, secure=True)

        shop_count = Shop.objects.count()
        self.assertEqual(shop_count, 1)

        response = self.client.delete('/api/v1/shops/84e8c5d7-5b05-4532-a9b8-3eb7f5f7b6cc', secure=True)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
