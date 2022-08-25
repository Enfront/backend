from django.urls import path

from .views import ShopView

app_name = 'shops'
urlpatterns = [
    path('shops', ShopView.as_view()),
    path('shops/<uuid:ref_id>', ShopView.as_view()),
]
