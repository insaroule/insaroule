from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from .views import set_user_language

urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),  # language switching
    path(
        "set_language/", set_user_language, name="set_user_language"
    ),  # custom language switching
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls", namespace="accounts")),
    path("", include("carpool.urls", namespace="carpool")),
    path("chat/", include("chat.urls", namespace="chat")),
]
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
