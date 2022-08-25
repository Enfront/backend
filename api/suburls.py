from django.urls import path, include

urlpatterns = [
    path('shop/', include('carts.urls', namespace='shops_carts')),
    path('shop/', include('orders.urls', namespace='shops_orders')),
    path('shop/', include('users.urls', namespace='shops_users')),
    path('shop/', include('themes.urls', namespace='shops_themes')),

    path('', include('themes.urls', namespace='shops_themes')),
]
