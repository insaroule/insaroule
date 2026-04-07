# chat/middleware.py
import logging
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)


@database_sync_to_async
def get_user_from_jwt(token_key):
    try:
        from django.contrib.auth import get_user_model
        from rest_framework_simplejwt.tokens import AccessToken

        User = get_user_model()
        access_token = AccessToken(token_key)
        logger.debug(
            "Find user from JWT token: %s",
            access_token,
            "user_id: %s",
            access_token["user_id"],
        )
        return User.objects.get(pk=access_token["user_id"])

    except Exception as e:
        logger.error("JWTAuthMiddleware error:", e)
        return None


class JWTAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        headers = dict(scope.get("headers", {}))
        logger.debug("Headers: %s", headers)
        auth_header = headers.get(b"authorization", b"").decode().split()

        if len(auth_header) == 2 and auth_header[0].lower() == "bearer":
            logger.debug("Found Bearer token in Authorization header")
            jwt_user = await get_user_from_jwt(auth_header[1])

            logger.debug("Authenticated user from JWT: %s", jwt_user)

            if jwt_user:
                scope["user"] = jwt_user

        return await self.inner(scope, receive, send)
