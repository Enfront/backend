from api.settings.core import *

from dotenv import load_dotenv

import btcpay
import stripe

# Take environment variables from .env-dev
dotenv_path = os.path.join(BASE_DIR, 'api/env', '.env-dev')
load_dotenv(dotenv_path)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ['SECRET_KEY']

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

CORS_ALLOWED_ORIGINS = ['http://localhost']
CORS_EXPOSE_HEADERS = ['Content-Type', 'X-CSRFToken']
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = ['http://localhost']
CSRF_COOKIE_SAMESITE = 'Lax'

SESSION_COOKIE_SAMESITE = 'Lax'

CSP_FRAME_ANCESTORS = ['http://localhost']
CSP_DEFAULT_SRC = ["'self'", 'https://www.recaptcha.net']


# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ['DEVELOPMENT_DB_NAME'],
        'HOST': os.environ['DEVELOPMENT_DB_HOST'],
        'USER': os.environ['DEVELOPMENT_DB_USER'],
        'PASSWORD': os.environ['DEVELOPMENT_DB_PASSWORD'],
        'PORT': int(os.environ['DEVELOPMENT_DB_PORT']),
    }
}


# Google Recaptcha
# https://pypi.org/project/django-recaptcha/

SILENCED_SYSTEM_CHECKS = ['captcha.recaptcha_test_key_error']


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
