"""ASGI config for project project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

from channels.auth import AuthMiddlewareStack
from chat.middleware import JWTAuthMiddleware
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from chat import routing
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings.development")


application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        # Add other protocols here if needed, e.g., WebSocket
        "websocket": AllowedHostsOriginValidator(
            JWTAuthMiddleware(
                AuthMiddlewareStack(URLRouter(routing.websocket_urlpatterns)),
            )
        ),
    },
)
