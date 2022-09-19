from django.urls import path

from .views import PaymentProviderView, PaymentProviderStripeIpn

from payments.paypal.paypal import PaymentPayPalView, PaymentPayPalIpnView
from payments.stripe.stripe import PaymentStripeView, PaymentStripeIpnView
from payments.btcpay.btcpay import PaymentCryptoView, PaymentCryptoIpnView

app_name = 'payments'
urlpatterns = [
    path('payments/paypal/ipn', PaymentPayPalIpnView.as_view()),
    path('payments/paypal/<str:paypal_id>/<uuid:order_ref>', PaymentPayPalView.as_view()),
    path('payments/paypal', PaymentPayPalView.as_view()),

    path('payments/crypto/ipn', PaymentCryptoIpnView.as_view()),
    path('payments/crypto/<uuid:order_ref>', PaymentCryptoView.as_view()),
    path('payments/crypto', PaymentCryptoView.as_view()),

    path('payments/stripe/account/ipn', PaymentProviderStripeIpn.as_view()),
    path('payments/stripe/ipn', PaymentStripeIpnView.as_view()),
    path('payments/stripe', PaymentStripeView.as_view()),

    path('payments/providers/<uuid:shop_ref>', PaymentProviderView.as_view()),
]
