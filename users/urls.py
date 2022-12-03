from django.urls import path, include

from users.views import (
    UserView,
    RegisterUserView,
    ForgotPasswordView,
    ResetPasswordView,
    ActivateUserView,
    LoginUserView,
    LoginTwoUserView,
    LogoutUserView,
    GetCsrfTokenView,
    CheckAuthStatusView,
    TwoFactorValidateView,
    TwoFactorDisableView,
)

app_name = 'users'
urlpatterns = [
    # Trench
    path('users/', include('trench.urls')),
    path('users/login/two-factor', LoginTwoUserView.as_view()),
    path('users/two-factor/validate', TwoFactorValidateView.as_view()),
    path('users/two-factor/disable', TwoFactorDisableView.as_view()),

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
