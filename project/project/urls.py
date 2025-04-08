from django.contrib import admin
from django.urls import path
from django.contrib.auth.views import LoginView, logout_then_login

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", LoginView.as_view(template_name="login.html"), name="login"),
    path("logout/", logout_then_login, name="logout"),
]
