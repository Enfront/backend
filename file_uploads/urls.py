from django.urls import path

from .views import FileUploadView

app_name = 'file_uploads'
urlpatterns = [
    path('files/<uuid:ref_id>', FileUploadView.as_view()),
]
