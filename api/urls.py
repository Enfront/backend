from django.urls import path, include

urlpatterns = [
    path('api/v1/', include('payouts.urls', namespace='payouts')),
    path('api/v1/', include('countries.urls', namespace='countries')),
    path('api/v1/', include('users.urls', namespace='users')),
    path('api/v1/', include('shops.urls', namespace='shops')),
    path('api/v1/', include('products.urls', namespace='products')),
    path('api/v1/', include('file_uploads.urls', namespace='file_uploads')),
    path('api/v1/', include('carts.urls', namespace='carts')),
    path('api/v1/', include('orders.urls', namespace='orders')),
    path('api/v1/', include('payments.urls', namespace='payments')),
    path('api/v1/', include('blacklists.urls', namespace='blacklists')),
    path('api/v1/', include('customers.urls', namespace='customers')),
    path('api/v1/', include('subscriptions.urls', namespace='subscriptions')),
    path('api/v1/', include('themes.urls', namespace='themes')),
]
