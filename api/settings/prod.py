from api.settings.core import *

from dotenv import load_dotenv

import btcpay
import stripe

# Take environment variables from .env
dotenv_path = os.path.join(BASE_DIR, 'api/env', '.env')
load_dotenv(dotenv_path)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ['SECRET_KEY']

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ['.enfront.io']

CORS_ALLOWED_ORIGINS = [
    'https://enfront.io',
    'https://*.enfront.io'
]

CORS_EXPOSE_HEADERS = ['Content-Type', 'X-CSRFToken']
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = [
    'https://enfront.io',
    'https://*.enfront.io'
]

CSRF_COOKIE_SAMESITE = 'Strict'
CSRF_COOKIE_SECURE = True

SESSION_COOKIE_SAMESITE = 'Strict'
SESSION_COOKIE_SECURE = True

SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

CSP_FRAME_ANCESTORS = [
    'https://enfront.io',
    'https://*.enfront.io'
]

CSP_DEFAULT_SRC = [
    "'self'",
    'https://www.recaptcha.net'
]


# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ['DB_NAME'],
        'HOST': os.environ['DB_HOST'],
        'USER': os.environ['DB_USER'],
        'PASSWORD': os.environ['DB_PASSWORD'],
        'PORT': int(os.environ['DB_PORT']),
    }
}


# PayPal SDK
# https://django-paypal.readthedocs.io/en/stable/

PAYPAL_TEST = False


# Google Recaptcha
# https://pypi.org/project/django-recaptcha/

RECAPTCHA_PUBLIC_KEY = os.environ['RECAPTCHA_PUBLIC_KEY']
RECAPTCHA_PRIVATE_KEY = os.environ['RECAPTCHA_PRIVATE_KEY']


# AWS Boto3
# https://pypi.org/project/boto3/

AWS_ACCESS_KEY_ID = os.environ['AWS_ACCESS_KEY_ID']
AWS_SECRET_ACCESS_KEY = os.environ['AWS_SECRET_ACCESS_KEY']
AWS_DEFAULT_REGION = os.environ['AWS_DEFAULT_REGION']

# BTCPay Server
# https://btcpayserver.org/

btcpay.api_key = os.environ['BTC_API_KEY']
btcpay.host_url = os.environ['BTC_HOST']
btcpay.store_id = os.environ['BTC_STORE_ID']


# Stripe
# https://pypi.org/project/stripe/
stripe.api_key = os.environ['STRIPE_KEY']
