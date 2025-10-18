# Create a UserNotificationPreferences every time a User is created
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in
from django.utils import translation

from accounts.models import User, UserNotificationPreferences


@receiver(post_save, sender=User)
def create_user_notification_preferences(sender, instance, created, **kwargs):
    if created:
        UserNotificationPreferences.objects.create(user=instance)


def set_language_on_login(sender, user, request, **kwargs):
    """
    Switch to user's preferred language on login and persist it with a cookie.
    Compatible with Django 4.x and 5.x.
    """
    lang = getattr(user, "preferred_language", None)

    # Validate language
    if not lang or lang not in dict(settings.LANGUAGES):
        return

    # 1️⃣ Activate immediately for this thread/request
    translation.activate(lang)
    request.LANGUAGE_CODE = lang

    # 2️⃣ Modify the response returned by the login view
    #    Django’s `LoginView` and `login()` both return a redirect response.
    #    The signal runs before the response, but we can patch it after login.
    def set_lang_cookie(response):
        response.set_cookie(
            settings.LANGUAGE_COOKIE_NAME,
            lang,
            max_age=60 * 60 * 24 * 365,  # 1 year
            samesite="Lax",
        )
        return response

    # Attach the function to the request so it’s executed after login response
    request.set_lang_cookie = set_lang_cookie


user_logged_in.connect(set_language_on_login)
