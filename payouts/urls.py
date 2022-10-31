from django.urls import path

from .views import PayoutView


app_name = 'payouts'
urlpatterns = [
    path('payouts/<uuid:shop_ref>', PayoutView.as_view()),
    path('payouts', PayoutView.as_view()),
]
