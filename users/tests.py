from django.contrib.auth import SESSION_KEY
from rest_framework import status
from rest_framework.test import APITestCase

from countries.models import Country
from customers.models import Customer
from shared.services import form_errors, get_url, reset_form_errors
from shops.models import Shop
from trench.models import MFAMethod
from users.models import User
from users.tokens import account_activation_token, forgot_password_token


class UserData(APITestCase):
    @classmethod
    def setUp(cls):
        cls.register_data = {
            'email': 'snow@castleblack.com',
            'username': 'YouKnowNothing',
            'first_name': 'John',
            'last_name': 'Snow',
            'password': 'ghost!123',
            'password_confirmation': 'ghost!123',
            'recaptcha': 'test',
            'shop': True,
        }

        cls.login_data = {
            'email': 'snow@castleblack.com',
            'password': 'ghost!123',
            'recaptcha': 'test',
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

    def create_customer(self, shop, is_active=True):
        if is_active:
            user = self.create_user()
        else:
            user = User.objects.create_user(**self.register_data)

        customer = Customer.objects.create(user=user, shop=shop)
        return customer

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


class TestUserView(UserData):
    def test_get_user_passing(self):
        user = self.create_user()

        self.client.post('/api/v1/users/login', self.login_data, secure=True)
        response = self.client.get('/api/v1/users', secure=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data'], {
            'ref_id': str(user.ref_id),
            'email': 'snow@castleblack.com',
            'username': 'YouKnowNothing',
            'first_name': 'John',
            'last_name': 'Snow',
            'subscription_tier': 0,
            'is_active': True,
            'created_at': user.created_at.isoformat().replace('+00:00', 'Z')
        })

    def test_get_user_not_logged_in(self):
        response = self.client.get('/api/v1/users', secure=True)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_user_passing(self):
        self.create_user()

        self.client.post('/api/v1/users/login', self.login_data, secure=True)
        response = self.client.patch('/api/v1/users', {'username': 'IKnowSomething'}, secure=True)
        updated_user = self.client.get('/api/v1/users', secure=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(updated_user.data['data']['username'], 'IKnowSomething')

    def test_patch_user_data_not_correct(self):
        self.create_user()
        self.client.post('/api/v1/users/login', self.login_data, secure=True)

        response = self.client.patch('/api/v1/users', {'username': False}, secure=True)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TestRegisterView(UserData):
    def test_owner_registration_passing(self):
        response = self.client.post('/api/v1/users/register', self.register_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user_count = User.objects.count()
        self.assertEqual(user_count, 1)

        mfa_method_count = MFAMethod.objects.count()
        self.assertEqual(mfa_method_count, 1)

    def test_customer_registration_passing(self):
        shop = self.create_shop()

        self.register_data['shop'] = False
        self.register_data['shop_name'] = 'The Wall'
        response = self.client.post('/api/v1/users/register', self.register_data, secure=True)

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, get_url('/activate', shop.name))
        self.assertEqual(form_errors, {})

        customer_count = Customer.objects.count()
        self.assertEqual(customer_count, 1)

    def test_customer_registration_no_shop_name(self):
        self.register_data['shop'] = False

        response = self.client.post('/api/v1/users/register', self.register_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

        customer_count = Customer.objects.count()
        self.assertEqual(customer_count, 0)

        user_count = User.objects.count()
        self.assertEqual(user_count, 0)

    def test_registration_duplicate_emails(self):
        self.client.post('/api/v1/users/register', self.register_data, secure=True)
       
        response = self.client.post('/api/v1/users/register', self.register_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

        user_count = User.objects.count()
        self.assertEqual(user_count, 1)

    def test_post_registration_customer_duplicate_emails(self):
        shop = self.create_shop()
        self.create_customer(shop)

        self.register_data['shop'] = False
        self.register_data['shop_name'] = 'The Wall'
        response = self.client.post('/api/v1/users/register', self.register_data, secure=True)

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, get_url('/register', shop.name))

        self.assertEqual(form_errors, {'form': {'message': 'A user with this email already exists.', 'status': 409}})
        reset_form_errors()

        customer_count = Customer.objects.count()
        self.assertEqual(customer_count, 1)

        user_count = User.objects.count()
        self.assertEqual(user_count, 2)

    def test_post_registration_passwords_dont_match(self):
        self.register_data['password'] = 'ygritte!123'
        self.register_data['password_confirmation'] = 'ghost!123'

        response = self.client.post('/api/v1/users/register', self.register_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

        user_count = User.objects.count()
        self.assertEqual(user_count, 0)

    def test_post_registration_customer_passwords_dont_match(self):
        shop = self.create_shop()
        self.register_data['shop'] = False
        self.register_data['shop_name'] = 'The Wall'
        self.register_data['password'] = 'ygritte!123'
        self.register_data['password_confirmation'] = 'ghost!123'

        response = self.client.post('/api/v1/users/register', self.register_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, get_url('/register', shop.name))
        self.assertEqual(form_errors, {
            'form': {
                'message': 'Password and password confirmation do not match.',
                'status': 422
            }
        })
        
        reset_form_errors()

        customer_count = Customer.objects.count()
        self.assertEqual(customer_count, 0)

        user_count = User.objects.count()
        self.assertEqual(user_count, 1)

    def test_post_registration_password_no_char(self):
        self.register_data['password'] = '!123'
        self.register_data['password_confirmation'] = '!123'

        response = self.client.post('/api/v1/users/register', self.register_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

        user_count = User.objects.count()
        self.assertEqual(user_count, 0)

    def test_post_registration_customer_password_no_char(self):
        shop = self.create_shop()
        self.register_data['shop'] = False
        self.register_data['shop_name'] = 'The Wall'
        self.register_data['password'] = '!123'
        self.register_data['password_confirmation'] = '!123'

        response = self.client.post('/api/v1/users/register', self.register_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, get_url('/register', shop.name))
        self.assertEqual(form_errors, {
            'password': {
                'message': 'Password must contain a letter.',
                'status': 422
            }
        })

        reset_form_errors()

        customer_count = Customer.objects.count()
        self.assertEqual(customer_count, 0)

        user_count = User.objects.count()
        self.assertEqual(user_count, 1)

    def test_post_registration_password_no_digit(self):
        self.register_data['password'] = 'ghost!'
        self.register_data['password_confirmation'] = 'ghost!'

        response = self.client.post('/api/v1/users/register', self.register_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

        user_count = User.objects.count()
        self.assertEqual(user_count, 0)

    def test_post_registration_customer_password_no_digit(self):
        shop = self.create_shop()
        self.register_data['shop'] = False
        self.register_data['shop_name'] = 'The Wall'
        self.register_data['password'] = 'ghost!'
        self.register_data['password_confirmation'] = 'ghost!'

        response = self.client.post('/api/v1/users/register', self.register_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, get_url('/register', shop.name))
        self.assertEqual(form_errors, {
            'password': {
                'message': 'Password must contain a digit.',
                'status': 422
            }
        })

        reset_form_errors()

        customer_count = Customer.objects.count()
        self.assertEqual(customer_count, 0)

        user_count = User.objects.count()
        self.assertEqual(user_count, 1)

    def test_post_registration_password_no_special_character(self):
        self.register_data['password'] = 'ghost123'
        self.register_data['password_confirmation'] = 'ghost123'

        response = self.client.post('/api/v1/users/register', self.register_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

        user_count = User.objects.count()
        self.assertEqual(user_count, 0)

    def test_post_registration_customer_password_no_special(self):
        shop = self.create_shop()
        self.register_data['shop'] = False
        self.register_data['shop_name'] = 'The Wall'
        self.register_data['password'] = 'ghost123'
        self.register_data['password_confirmation'] = 'ghost123'

        response = self.client.post('/api/v1/users/register', self.register_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, get_url('/register', shop.name))
        self.assertEqual(form_errors, {
            'password': {
                'message': 'Password must contain a special character.',
                'status': 422
            }
        })

        reset_form_errors()

        customer_count = Customer.objects.count()
        self.assertEqual(customer_count, 0)

        user_count = User.objects.count()
        self.assertEqual(user_count, 1)


class TestForgotPasswordView(UserData):
    def test_post_forgot_password_passing(self):
        self.create_user()
        
        response = self.client.post('/api/v1/users/forgot', self.login_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post_forgot_password_customer_passing(self):
        shop = self.create_shop()
        self.create_customer(shop)

        self.login_data['shop'] = False
        self.login_data['shop_name'] = 'The Wall'
        response = self.client.post('/api/v1/users/forgot', self.login_data, secure=True)

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, get_url('/', shop.name))
        self.assertEqual(form_errors, {})

    def test_post_forgot_password_customer_no_shop_name(self):
        shop = self.create_shop()
        self.create_customer(shop)

        self.login_data['shop'] = False
        response = self.client.post('/api/v1/users/forgot', self.login_data, secure=True)

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_post_forgot_password_no_email(self):
        self.create_user()

        response = self.client.post('/api/v1/users/forgot', {'shop': True}, secure=True)
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_forgot_password_customer_no_email(self):
        shop = self.create_shop()
        self.create_customer(shop)

        response = self.client.post('/api/v1/users/forgot', {'shop_name': 'The Wall'}, secure=True)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, get_url('/forgot', shop.name))

        self.assertEqual(form_errors, {'form': {'message': 'Email must be provided.', 'status': 422}})
        reset_form_errors()

    def test_post_forgot_password_email_does_not_exist(self):
        response = self.client.post('/api/v1/users/forgot', self.login_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_post_forgot_password_customer_email_does_not_exist(self):
        shop = self.create_shop()
        forgot_password_data = {
            'email': 'test@mail.com',
            'shop_name': 'The Wall',
            'recaptcha': 'test'
        }

        response = self.client.post('/api/v1/users/forgot', forgot_password_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, get_url('/forgot', shop.name))
        self.assertEqual(form_errors, {
            'form': {
                'message': 'A user with the email test@mail.com does not exist.',
                'status': 404
            }
        })

        reset_form_errors()


class TestResetPasswordView(UserData):
    def test_post_reset_password_passing(self):
        user = self.create_user()
        token = forgot_password_token.make_token(user)
        reset_data = {
            'ref_id': user.ref_id,
            'password': 'newPass!123',
            'password_confirmation': 'newPass!123',
            'token': token,
            'shop': True
        }

        response = self.client.post('/api/v1/users/reset', reset_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, get_url('/'))

        updated_user = User.objects.get(ref_id=user.ref_id)
        self.assertNotEqual(user.password, updated_user.password)

    def test_post_reset_password_customer_passing(self):
        shop = self.create_shop()
        self.create_customer(shop)

        user = User.objects.get(email='snow@castleblack.com', customer__shop=shop)
        token = forgot_password_token.make_token(user)
        reset_data = {
            'ref_id': user.ref_id,
            'password': 'newPass!123',
            'password_confirmation': 'newPass!123',
            'token': token,
            'shop_name': 'The Wall'
        }

        response = self.client.post('/api/v1/users/reset', reset_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, get_url('/', shop.name))

        updated_user = User.objects.get(ref_id=user.ref_id)
        self.assertNotEqual(user.password, updated_user.password)

    def test_post_reset_password_customer_no_shop_name(self):
        shop = self.create_shop()
        self.create_customer(shop)

        self.login_data['shop'] = False
        response = self.client.post('/api/v1/users/reset', self.login_data, secure=True)

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_post_reset_password_no_ref_id(self):
        user = self.create_user()
        token = forgot_password_token.make_token(user)
        reset_data = {
            'password': 'newPass!123',
            'password_confirmation': 'newPass!123',
            'token': token,
            'shop': True
        }

        response = self.client.post('/api/v1/users/reset', reset_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

        updated_user = User.objects.get(ref_id=user.ref_id)
        self.assertEqual(user.password, updated_user.password)

    def test_post_reset_password_customer_no_ref_id(self):
        shop = self.create_shop()
        self.create_customer(shop)

        user = User.objects.get(email='snow@castleblack.com', customer__shop=shop)
        token = forgot_password_token.make_token(user)
        reset_data = {
            'password': 'newPass!123',
            'password_confirmation': 'newPass!123',
            'token': token,
            'shop_name': 'The Wall'
        }

        response = self.client.post('/api/v1/users/reset', reset_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, get_url('/forgot', shop.name))

        self.assertEqual(form_errors, {'form': {'message': 'A user ref id must be provided.', 'status': 422}})
        reset_form_errors()

        updated_user = User.objects.get(ref_id=user.ref_id)
        self.assertEqual(user.password, updated_user.password)

    def test_post_reset_password_no_token(self):
        user = self.create_user()
        reset_data = {
            'ref_id': user.ref_id,
            'password': 'newPass!123',
            'password_confirmation': 'newPass!123',
            'shop': True
        }

        response = self.client.post('/api/v1/users/reset', reset_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

        updated_user = User.objects.get(ref_id=user.ref_id)
        self.assertEqual(user.password, updated_user.password)

    def test_post_reset_password_customer_no_token(self):
        shop = self.create_shop()
        self.create_customer(shop)

        user = User.objects.get(email='snow@castleblack.com', customer__shop=shop)
        reset_data = {
            'ref_id': user.ref_id,
            'password': 'newPass!123',
            'password_confirmation': 'newPass!123',
            'shop_name': 'The Wall'
        }

        response = self.client.post('/api/v1/users/reset', reset_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, get_url('/forgot', shop.name))

        self.assertEqual(form_errors, {'form': {'message': 'A token must be provided.', 'status': 422}})
        reset_form_errors()

        updated_user = User.objects.get(ref_id=user.ref_id)
        self.assertEqual(user.password, updated_user.password)

    def test_post_reset_password_no_password(self):
        user = self.create_user()
        token = forgot_password_token.make_token(user)
        reset_data = {
            'ref_id': user.ref_id,
            'token': token,
            'shop': True
        }

        response = self.client.post('/api/v1/users/reset', reset_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

        updated_user = User.objects.get(ref_id=user.ref_id)
        self.assertEqual(user.password, updated_user.password)

    def test_post_reset_password_customer_no_password(self):
        shop = self.create_shop()
        self.create_customer(shop)

        user = User.objects.get(email='snow@castleblack.com', customer__shop=shop)
        token = forgot_password_token.make_token(user)
        reset_data = {
            'ref_id': user.ref_id,
            'token': token,
            'shop_name': 'The Wall'
        }

        response = self.client.post('/api/v1/users/reset', reset_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, get_url('/forgot', shop.name))

        self.assertEqual(form_errors, {'form': {'message': 'A new password must be provided.', 'status': 422}})
        reset_form_errors()

        updated_user = User.objects.get(ref_id=user.ref_id)
        self.assertEqual(user.password, updated_user.password)

    def test_post_reset_password_data_not_correct(self):
        user = self.create_user()
        token = forgot_password_token.make_token(user)
        reset_data = {
            'ref_id': user.ref_id,
            'password': True,
            'password_confirmation': True,
            'token': token,
            'shop': True
        }

        response = self.client.post('/api/v1/users/reset', reset_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        updated_user = User.objects.get(ref_id=user.ref_id)
        self.assertEqual(user.password, updated_user.password)

    def test_post_reset_password_customer_data_not_correct(self):
        shop = self.create_shop()
        self.create_customer(shop)

        user = User.objects.get(email='snow@castleblack.com', customer__shop=shop)
        token = forgot_password_token.make_token(user)
        reset_data = {
            'ref_id': user.ref_id,
            'password': True,
            'password_confirmation': True,
            'token': token,
            'shop_name': 'The Wall'
        }

        response = self.client.post('/api/v1/users/reset', reset_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, get_url('/forgot', shop.name))
        self.assertEqual(form_errors, {
            'form': {
                'message': 'There was a problem changing your password.',
                'status': 400
            }
        })

        reset_form_errors()

        updated_user = User.objects.get(ref_id=user.ref_id)
        self.assertEqual(user.password, updated_user.password)

    def test_post_reset_password_user_does_not_exist(self):
        user = self.create_user()
        token = forgot_password_token.make_token(user)
        reset_data = {
            'ref_id': 'fabfc6f8-032b-443e-8710-06ec5fb37332',
            'password': 'newPass!123',
            'password_confirmation': 'newPass!123',
            'token': token,
            'shop': True
        }

        response = self.client.post('/api/v1/users/reset', reset_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        updated_user = User.objects.get(ref_id=user.ref_id)
        self.assertEqual(user.password, updated_user.password)

    def test_post_reset_password_customer_user_does_not_exist(self):
        shop = self.create_shop()
        self.create_customer(shop)

        user = User.objects.get(email='snow@castleblack.com', customer__shop=shop)
        token = forgot_password_token.make_token(user)
        reset_data = {
            'ref_id': 'fabfc6f8-032b-443e-8710-06ec5fb37332',
            'password': 'newPass!123',
            'password_confirmation': 'newPass!123',
            'token': token,
            'shop_name': 'The Wall'
        }

        response = self.client.post('/api/v1/users/reset', reset_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, get_url('/forgot', shop.name))
        self.assertEqual(form_errors, {
            'form': {
                'message': 'A user with the ref id fabfc6f8-032b-443e-8710-06ec5fb37332 does not exist.',
                'status': 404
            }
        })

        reset_form_errors()

        updated_user = User.objects.get(ref_id=user.ref_id)
        self.assertEqual(user.password, updated_user.password)

    def test_post_reset_password_bad_token(self):
        user = self.create_user()
        reset_data = {
            'ref_id': user.ref_id,
            'password': 'newPass!123',
            'password_confirmation': 'newPass!123',
            'token': 'token',
            'shop': True
        }

        response = self.client.post('/api/v1/users/reset', reset_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        updated_user = User.objects.get(ref_id=user.ref_id)
        self.assertEqual(user.password, updated_user.password)

    def test_post_reset_password_customer_bad_token(self):
        shop = self.create_shop()
        self.create_customer(shop)

        user = User.objects.get(email='snow@castleblack.com', customer__shop=shop)
        reset_data = {
            'ref_id': user.ref_id,
            'password': 'newPass!123',
            'password_confirmation': 'newPass!123',
            'token': 'token',
            'shop_name': 'The Wall'
        }

        response = self.client.post('/api/v1/users/reset', reset_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, get_url('/forgot', shop.name))

        self.assertEqual(form_errors, {'form': {'message': 'The reset token is not valid.', 'status': 401}})
        reset_form_errors()

        updated_user = User.objects.get(ref_id=user.ref_id)
        self.assertEqual(user.password, updated_user.password)


class TestActivateView(UserData):
    def test_get_activate_user_passing(self):
        user = User.objects.create_user(**self.register_data)
        self.assertEqual(user.is_active, False)

        token = account_activation_token.make_token(user)
        response = self.client.get('/api/v1/users/activate', {'ref_id': user.ref_id, 'token': token}, secure=True)

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, get_url('/'))

        updated_user = User.objects.get(ref_id=user.ref_id)
        self.assertEqual(updated_user.is_active, True)

    def test_get_activate_user_customer_passing(self):
        shop = self.create_shop()
        self.create_customer(shop, False)

        user = User.objects.get(email='snow@castleblack.com', customer__shop=shop)
        self.assertEqual(user.is_active, False)

        token = account_activation_token.make_token(user)
        activate_data = {
            'ref_id': user.ref_id,
            'token': token,
            'shop': 'The Wall'
        }

        response = self.client.get('/api/v1/users/activate', activate_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, get_url('/', shop.name))

        updated_user = User.objects.get(ref_id=user.ref_id)
        self.assertEqual(updated_user.is_active, True)

    def test_get_activate_user_bad_ref_id(self):
        user = User.objects.create_user(**self.register_data)
        token = account_activation_token.make_token(user)
        activate_data = {
            'ref_id': 'fabfc6f8-032b-443e-8710-06ec5fb37332',
            'token': token,
        }

        response = self.client.get('/api/v1/users/activate', activate_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        updated_user = User.objects.get(ref_id=user.ref_id)
        self.assertEqual(updated_user.is_active, False)

    def test_get_activate_user_customer_bad_ref_id(self):
        shop = self.create_shop()
        self.create_customer(shop, False)

        user = User.objects.get(email='snow@castleblack.com', customer__shop=shop)
        self.assertEqual(user.is_active, False)

        token = account_activation_token.make_token(user)
        activate_data = {
            'ref_id': 'fabfc6f8-032b-443e-8710-06ec5fb37332',
            'token': token,
            'shop': 'The Wall'
        }

        response = self.client.get('/api/v1/users/activate', activate_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, get_url('/login', shop.name))
        self.assertEqual(form_errors, {
            'form': {
                'message': 'A user with the ref id fabfc6f8-032b-443e-8710-06ec5fb37332 does not exist.',
                'status': 404
            }
        })

        reset_form_errors()

        updated_user = User.objects.get(ref_id=user.ref_id)
        self.assertEqual(updated_user.is_active, False)

    def test_get_activate_user_bad_token(self):
        user = User.objects.create_user(**self.register_data)
        self.assertEqual(user.is_active, False)

        response = self.client.get('/api/v1/users/activate', {'ref_id': user.ref_id, 'token': 'token'}, secure=True)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        updated_user = User.objects.get(ref_id=user.ref_id)
        self.assertEqual(updated_user.is_active, False)

    def test_get_activate_user_customer_bad_token(self):
        shop = self.create_shop()
        self.create_customer(shop, False)

        user = User.objects.get(email='snow@castleblack.com', customer__shop=shop)
        self.assertEqual(user.is_active, False)

        activate_data = {
            'ref_id': user.ref_id,
            'token': 'token',
            'shop': 'The Wall'
        }

        response = self.client.get('/api/v1/users/activate', activate_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, get_url('/login', shop.name))

        self.assertEqual(form_errors, {'form': {'message': 'The activate token is not valid.', 'status': 401}})
        reset_form_errors()

        updated_user = User.objects.get(ref_id=user.ref_id)
        self.assertEqual(updated_user.is_active, False)


class TestLoginView(UserData):
    def test_post_login_passing(self):
        self.create_user()

        response = self.client.post('/api/v1/users/login', self.login_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(SESSION_KEY in self.client.session)

    def test_post_login_customer_no_shop_name(self):
        self.create_user()

        self.login_data['shop'] = False
        response = self.client.post('/api/v1/users/login', self.login_data, secure=True)

        self.assertEqual(response.url, get_url('/404'))
        self.assertFalse(SESSION_KEY in self.client.session)

    def test_post_login_no_email(self):
        self.create_user()

        # noinspection PyTypedDict
        self.login_data['email'] = None
        response = self.client.post('/api/v1/users/login', self.login_data, secure=True)

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertFalse(SESSION_KEY in self.client.session)

    def test_post_login_customer_no_email(self):
        shop = self.create_shop()
        self.create_customer(shop)

        user = User.objects.get(email='snow@castleblack.com', customer__shop=shop)
        user.is_active = True
        user.save()

        # noinspection PyTypedDict
        self.login_data['email'] = None
        self.login_data['shop'] = False
        self.login_data['shop_name'] = 'The Wall'
        response = self.client.post('/api/v1/users/login', self.login_data, secure=True)

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, get_url('/login', shop.name))

        self.assertEqual(form_errors, {'form': {'message': 'An email must be provided.', 'status': 422}})
        reset_form_errors()

        self.assertFalse(SESSION_KEY in self.client.session)

    def test_post_login_no_password(self):
        self.create_user()

        # noinspection PyTypedDict
        self.login_data['password'] = None
        response = self.client.post('/api/v1/users/login', self.login_data, secure=True)

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertFalse(SESSION_KEY in self.client.session)

    def test_post_login_customer_no_password(self):
        shop = self.create_shop()
        self.create_customer(shop)

        user = User.objects.get(email='snow@castleblack.com', customer__shop=shop)
        user.is_active = True
        user.save()

        # noinspection PyTypedDict
        self.login_data['password'] = None
        self.login_data['shop'] = False
        self.login_data['shop_name'] = 'The Wall'
        response = self.client.post('/api/v1/users/login', self.login_data, secure=True)

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, get_url('/login', shop.name))

        self.assertEqual(form_errors, {'form': {'message': 'A password must be provided.', 'status': 422}})
        reset_form_errors()

        self.assertFalse(SESSION_KEY in self.client.session)

    def test_post_login_wrong_password(self):
        self.create_user()

        self.login_data['password'] = 'wrong password'
        response = self.client.post('/api/v1/users/login', self.login_data, secure=True)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertTrue(SESSION_KEY not in self.client.session)

    def test_post_login_customer_wrong_password(self):
        shop = self.create_shop()
        self.create_customer(shop)

        user = User.objects.get(email='snow@castleblack.com', customer__shop=shop)
        user.is_active = True
        user.save()

        self.login_data['password'] = 'wrong password'
        self.login_data['shop'] = False
        self.login_data['shop_name'] = 'The Wall'
        response = self.client.post('/api/v1/users/login', self.login_data, secure=True)

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, get_url('/login', shop.name))

        self.assertEqual(form_errors, {'form': {'message': 'Email and/or password is incorrect.', 'status': 401}})
        reset_form_errors()

        self.assertFalse(SESSION_KEY in self.client.session)


class TestLogoutView(UserData):
    def test_post_logout_passing(self):
        self.create_user()

        response = self.client.post('/api/v1/users/login', self.login_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(SESSION_KEY in self.client.session)

        self.client.post('/api/v1/users/logout', self.login_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(SESSION_KEY in self.client.session)

    def test_post_logout_customer_passing(self):
        shop = self.create_shop()
        self.create_customer(shop)

        user = User.objects.get(email='snow@castleblack.com', customer__shop=shop)
        user.is_active = True
        user.save()

        self.login_data['shop'] = False
        self.login_data['shop_name'] = 'The Wall'
        login_response = self.client.post('/api/v1/users/login', self.login_data, secure=True)

        self.assertEqual(login_response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(login_response.url, get_url('/', shop.name))
        self.assertTrue(SESSION_KEY in self.client.session)

        self.login_data['shop'] = False
        self.login_data['shop_name'] = 'The Wall'
        logout_response = self.client.post('/api/v1/users/logout', self.login_data, secure=True)

        self.assertEqual(logout_response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(logout_response.url, get_url('/', shop.name))
        self.assertFalse(SESSION_KEY in self.client.session)

    def test_post_logout_customer_no_shop_name(self):
        shop = self.create_shop()
        self.create_customer(shop)

        user = User.objects.get(email='snow@castleblack.com', customer__shop=shop)
        user.is_active = True
        user.save()

        self.login_data['shop'] = False
        self.login_data['shop_name'] = 'The Wall'
        login_response = self.client.post('/api/v1/users/login', self.login_data, secure=True)

        self.assertEqual(login_response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(login_response.url, get_url('/', shop.name))
        self.assertTrue(SESSION_KEY in self.client.session)

        self.login_data['shop'] = False
        self.login_data['shop_name'] = None
        logout_response = self.client.post('/api/v1/users/logout', self.login_data, secure=True)

        self.assertEqual(logout_response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)


class TestOtherUserViews(UserData):
    def test_get_csrf_token_passing(self):
        response = self.client.get('/api/v1/users/csrf', secure=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response['X-CSRFToken'])

    def test_get_auth_session_passing(self):
        self.create_user()

        response = self.client.post('/api/v1/users/login', self.login_data, secure=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_two = self.client.get('/api/v1/users/status', secure=True)
        self.assertEqual(response_two.status_code, status.HTTP_200_OK)

    def test_get_auth_session_not_logged_in(self):
        response = self.client.get('/api/v1/users/status', secure=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], False)
