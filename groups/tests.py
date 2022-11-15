from rest_framework.test import APITestCase
from rest_framework import status

from countries.models import Country
from groups.models import Collection
from products.models import Product
from shops.models import Shop
from users.models import User
from themes.models import Theme, ThemeConfiguration


class TestShopView(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.login_data = {
            'email': 'snow@castleblack.com',
            'password': 'ghost!123',
            'shop': True
        }

        register_data = {
            'email': 'snow@castleblack.com',
            'username': 'YouKnowNothing',
            'first_name': 'John',
            'last_name': 'Snow',
            'password': 'ghost!123',
            'password_confirmation': 'ghost!123',
            'shop': True,
        }

        user = User.objects.create_user(**register_data)
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

        shop_data = {
            'name': 'The Wall',
            'domain': 'https://castleblack.com',
            'email': 'snow@castleblack.com',
            'description': 'We sell harvested white walker souls.',
            'currency': 'USD',
            'country': country,
            'owner_id': user.id
        }

        shop = Shop.objects.create(**shop_data)
        cls.shop = shop

        configuration_data = {
            'shop': shop,
            'theme': theme,
            'file_name': 'test_file.json',
            'status': 1
        }

        ThemeConfiguration.objects.create(**configuration_data)

        product_data = {
            'name': 'Iron Throne',
            'price': 999,
            'shop': shop
        }

        product = Product.objects.create(**product_data)
        cls.product = product

    @classmethod
    def setUp(cls):
        cls.collection_data = {
            'title': 'Royalty Items',
            'slug': 'royalty-items',
            'products': [cls.product.ref_id],
            'shop': cls.shop.ref_id
        }

    def test_get_collection(self):
        self.client.post('/api/v1/users/login', self.login_data, secure=True)
        response = self.client.post('/api/v1/collections', self.collection_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        get_response = self.client.get('/api/v1/collections', secure=True)
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        self.assertEqual(get_response.data['data'][0]['title'], 'Royalty Items')

    def test_get_collection_that_does_not_exist(self):
        self.client.post('/api/v1/users/login', self.login_data, secure=True)
        response = self.client.get('/api/v1/collections', secure=True)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_create_collection(self):
        self.client.post('/api/v1/users/login', self.login_data, secure=True)
        response = self.client.post('/api/v1/collections', self.collection_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_collection_with_duplicate_slug(self):
        self.client.post('/api/v1/users/login', self.login_data, secure=True)
        response = self.client.post('/api/v1/collections', self.collection_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response_two = self.client.post('/api/v1/collections', self.collection_data, secure=True)
        self.assertEqual(response_two.status_code, status.HTTP_409_CONFLICT)

        collection = Collection.objects.filter(ref_id=response.data['data']['ref_id'])
        self.assertEqual(collection.count(), 1)

    def test_create_collection_with_invalid_product(self):
        self.collection_data['products'] = ['invalid_product']
        self.client.post('/api/v1/users/login', self.login_data, secure=True)
        response = self.client.post('/api/v1/collections', self.collection_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_collection(self):
        self.client.post('/api/v1/users/login', self.login_data, secure=True)
        response = self.client.post('/api/v1/collections', self.collection_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.collection_data['title'] = 'New Title'
        self.collection_data['slug'] = 'new-title'
        self.collection_data['products'] = [self.product.ref_id]

        patch_response = self.client.patch(
            '/api/v1/collections/{}'.format(response.data['data']['ref_id']),
            self.collection_data,
            secure=True
        )

        collection = Collection.objects.get(ref_id=response.data['data']['ref_id'])
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertEqual(collection.title, 'New Title')
        self.assertEqual(collection.slug, 'new-title')

    def test_update_collection_with_invalid_ref_id(self):
        self.client.post('/api/v1/users/login', self.login_data, secure=True)
        response = self.client.post('/api/v1/collections', self.collection_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.collection_data['title'] = 'New Title'
        self.collection_data['slug'] = 'new-title'
        patch_response = self.client.patch(
            '/api/v1/collections/84e8c5d7-5b05-4532-a9b8-3eb7f5f7b6cc',
            self.collection_data,
            secure=True
        )

        self.assertEqual(patch_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_collection_with_duplicate_slug(self):
        self.client.post('/api/v1/users/login', self.login_data, secure=True)
        response = self.client.post('/api/v1/collections', self.collection_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        collection_data_two = {
            'title': 'Royalty Items',
            'slug': 'royalty-items-different',
            'products': [self.product.ref_id],
            'shop': self.shop.ref_id
        }

        response_two = self.client.post('/api/v1/collections', collection_data_two, secure=True)
        self.assertEqual(response_two.status_code, status.HTTP_201_CREATED)

        collection_data_two['slug'] = 'royalty-items'
        patch_response_two = self.client.patch(
            '/api/v1/collections/{}'.format(response_two.data['data']['ref_id']),
            collection_data_two,
            secure=True
        )

        self.assertEqual(patch_response_two.status_code, status.HTTP_409_CONFLICT)

    def test_delete_collection(self):
        self.client.post('/api/v1/users/login', self.login_data, secure=True)
        response = self.client.post('/api/v1/collections', self.collection_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        delete_response = self.client.delete(
            '/api/v1/collections/{}'.format(response.data['data']['ref_id']),
            secure=True
        )

        collection = Collection.objects.filter(ref_id=response.data['data']['ref_id'])
        self.assertEqual(collection.count(), 0)
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_collection_with_invalid_ref_id(self):
        self.client.post('/api/v1/users/login', self.login_data, secure=True)
        response = self.client.post('/api/v1/collections', self.collection_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        delete_response = self.client.delete('/api/v1/collections/84e8c5d7-5b05-4532-a9b8-3eb7f5f7b6cc', secure=True)
        self.assertEqual(delete_response.status_code, status.HTTP_404_NOT_FOUND)
