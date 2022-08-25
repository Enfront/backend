from django.urls import path

from .views import SubscriptionStripeView, SubscriptionStripeIpnView

app_name = 'subscriptions'
urlpatterns = [
    path('subscriptions/stripe/ipn', SubscriptionStripeIpnView.as_view()),
    path('subscriptions/stripe/<str:subscription_id>', SubscriptionStripeView.as_view()),
    path('subscriptions/stripe', SubscriptionStripeView.as_view()),
    path('subscriptions/<str:user_ref>/<str:shop_ref>', SubscriptionStripeView.as_view()),
]
