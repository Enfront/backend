from django.urls import path

from .views import OrderView, OrderCommentView, OrderStatView


app_name = 'orders'
urlpatterns = [
    path('checkout', OrderView.as_view()),

    path('orders/shop/<uuid:shop_ref>', OrderView.as_view()),
    path('orders/stats/shop/<uuid:shop_ref>', OrderStatView.as_view()),

    path('orders/comments/<uuid:comment_ref>', OrderCommentView.as_view()),
    path('orders/comments', OrderCommentView.as_view()),

    path('orders/checkout/<uuid:order_ref>', OrderView.as_view()),
    path('orders/<uuid:order_ref>', OrderView.as_view()),
    path('orders', OrderView.as_view()),
]
