from django.urls import path

from .views import CustomerView, CustomerNotesView

app_name = 'customers'
urlpatterns = [
    path('customers/shop/<uuid:shop_ref>', CustomerView.as_view()),
    path('customers/<uuid:customer_ref>/shop/<uuid:shop_ref>', CustomerView.as_view()),

    # Notes
    path('customers/<uuid:customer_ref>/note', CustomerNotesView.as_view()),
    path('customers/note/<uuid:note_ref>', CustomerNotesView.as_view()),
    path('customers/note', CustomerNotesView.as_view()),

    path('customers', CustomerView.as_view()),
]
