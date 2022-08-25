from django.urls import path

from .views import ProductView

app_name = 'shops'
urlpatterns = [
    path('products', ProductView.as_view()),
    path('products/<uuid:product_ref>', ProductView.as_view()),
    path('products/shop/<uuid:shop_ref>', ProductView.as_view()),
    path('products/digital/<uuid:digital_ref>', ProductView.as_view()),
]
