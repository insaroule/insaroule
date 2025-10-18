from django.contrib.auth import views as auth_views
from accounts.views.registration import CustomLoginView as LoginView
from django.urls import path, reverse_lazy

from accounts.forms import PasswordResetForm, SetPasswordForm
from accounts.views import profile, register
from accounts.views.verify_email import (
    verify_email_complete,
    verify_email_confirm,
    verify_email_send_token,
    verify_email_sent,
)

app_name = "accounts"

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", auth_views.logout_then_login, name="logout"),
    path("register/", register, name="register"),
    path("", profile.user_profile, name="me"),
    path("delete/", profile.delete_profile, name="account_close"),
    path("email/change/", profile.email_change, name="email_change"),
    path("export/", profile.export, name="export"),
]

# Email verification URLs
urlpatterns += [
    path("register/email/", verify_email_send_token, name="verify_email_send_token"),
    path("register/email/sent/", verify_email_sent, name="verify_email_sent"),
    path(
        "register/email/confirm/<uidb64>/<token>/",
        verify_email_confirm,
        name="verify_email_confirm",
    ),
    path(
        "register/email/complete/",
        verify_email_complete,
        name="verify_email_complete",
    ),
]

# Password reset URLs
urlpatterns += [
    path(
        "password_reset/",
        auth_views.PasswordResetView.as_view(
            success_url=reverse_lazy("accounts:password_reset_done"),
            form_class=PasswordResetForm,
            template_name="registration/password_reset/index.html",
        ),
        name="password_reset",
    ),
    path(
        "password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset/done.html",
        ),
        name="password_reset_done",
    ),
    path(
        "password_reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            form_class=SetPasswordForm,
            success_url=reverse_lazy("accounts:password_reset_complete"),
            template_name="registration/password_reset/index.html",
        ),
        name="password_reset_confirm",
    ),
    path(
        "password_reset/complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset/complete.html",
        ),
        name="password_reset_complete",
    ),
    path(
        "password_change/",
        profile.PasswordChangeView.as_view(),
        name="password_change",
    ),
]
