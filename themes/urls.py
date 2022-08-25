from django.urls import path

from .views import ThemeView, ThemeConfigurationView, ThemeSettingsView, ThemeTemplateView

app_name = 'themes'
urlpatterns = [
    path('themes/<uuid:theme_ref>/config/<uuid:shop_ref>', ThemeConfigurationView.as_view()),
    path('themes/config', ThemeConfigurationView.as_view()),

    path('themes/<uuid:theme_ref>/settings', ThemeSettingsView.as_view()),

    path('themes/<uuid:theme_ref>', ThemeView.as_view()),
    path('themes', ThemeView.as_view()),

    # Wildcard subdomains
    path('<slug:page>/<slug:item_slug>', ThemeTemplateView.as_view()),
    path('<slug:page>', ThemeTemplateView.as_view()),
    path('', ThemeTemplateView.as_view()),
]
