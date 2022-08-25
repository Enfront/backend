from django.urls import path

from .views import CartView, CartAddItemView, CartRemoveItemView

app_name = 'cart'
urlpatterns = [
    path('cart/remove', CartRemoveItemView.as_view()),
    path('cart/add', CartAddItemView.as_view()),
    path('cart', CartView.as_view()),
]
