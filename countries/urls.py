from django.urls import path

from .views import CountryView

app_name = 'countries'
urlpatterns = [
    path('countries', CountryView.as_view()),
]
