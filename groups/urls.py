from django.urls import path

from .views import CollectionView

app_name = 'collections'
urlpatterns = [
    path('collections', CollectionView.as_view()),
    path('collections/<uuid:collection_ref>', CollectionView.as_view()),
]
