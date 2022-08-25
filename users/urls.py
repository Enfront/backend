from django.urls import path

from users.views import (
    UserView,
    RegisterUserView,
    ForgotPasswordView,
    ResetPasswordView,
    ActivateUserView,
    LoginUserView,
    LogoutUserView,
    GetCsrfTokenView,
    CheckAuthStatusView,
)

app_name = 'users'
urlpatterns = [
    # Users
    path('users', UserView.as_view()),
    path('users/self', UserView.as_view()),

    # Authentication
    path('users/register', RegisterUserView.as_view()),
    path('users/forgot', ForgotPasswordView.as_view()),
    path('users/reset', ResetPasswordView.as_view()),
    path('users/activate', ActivateUserView.as_view()),
    path('users/login', LoginUserView.as_view()),
    path('users/logout', LogoutUserView.as_view()),
    path('users/csrf', GetCsrfTokenView.as_view()),
    path('users/status', CheckAuthStatusView.as_view()),
]
