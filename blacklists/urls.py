from django.urls import path

from .views import BlacklistView

app_name = 'blacklists'
urlpatterns = [
    path('blacklists', BlacklistView.as_view()),
    path('blacklists/delete/<uuid:ref_id>', BlacklistView.as_view()),
    path('blacklists/<uuid:shop_ref>', BlacklistView.as_view())
]
