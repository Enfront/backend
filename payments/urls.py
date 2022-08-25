from django.urls import path

from .views import (
    PaymentsPayPalView,
    PaymentsProviderPayPalView,
    PaymentsStripeView,
    PaymentsStripeIpnView,
    PaymentsProviderStripeView,
    PaymentsProviderStripeIpn
)

app_name = 'payments'
urlpatterns = [
    path('payments/paypal/<str:paypal_id>/<uuid:order_ref>', PaymentsPayPalView.as_view()),
    path('payments/paypal/<uuid:shop_ref>', PaymentsProviderPayPalView.as_view()),
    path('payments/paypal', PaymentsPayPalView.as_view()),

    path('payments/stripe/ipn', PaymentsStripeIpnView.as_view()),
    path('payments/stripe/account/ipn', PaymentsProviderStripeIpn.as_view()),
    path('payments/stripe/<uuid:shop_ref>', PaymentsProviderStripeView.as_view()),
    path('payments/stripe', PaymentsStripeView.as_view()),
]
