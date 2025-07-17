from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls", namespace="accounts")),
    path("", include("carpool.urls", namespace="carpool")),
    path("chat/", include("chat.urls", namespace="chat")),
]

if settings.DEBUG:
    from django.views.static import serve

    urlpatterns += [
        path(
            "favicon.ico",
            serve,
            {
                "path": "favicon.ico",
                "document_root": settings.STATIC_ROOT,
            },
        ),
        path(
            "site.webmanifest",
            serve,
            {
                "path": "site.webmanifest",
                "document_root": settings.STATIC_ROOT,
            },
        ),
        path(
            "apple-touch-icon.png",
            serve,
            {
                "path": "apple-touch-icon.png",
                "document_root": settings.STATIC_ROOT,
            },
        ),
        path(
            "favicon-32x32.png",
            serve,
            {
                "path": "favicon-32x32.png",
                "document_root": settings.STATIC_ROOT,
            },
        ),
        path(
            "favicon-16x16.png",
            serve,
            {
                "path": "favicon-16x16.png",
                "document_root": settings.STATIC_ROOT,
            },
        ),
    ]

    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
