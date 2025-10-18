from django.conf import settings
from django.utils.translation import activate
from django.views.decorators.csrf import csrf_exempt
from django.views.i18n import set_language as django_set_language

import logging

logger = logging.getLogger(__name__)


@csrf_exempt
def set_user_language(request):
    """
    Wrap Django's set_language view to also update user's preferred_language.
    """
    response = django_set_language(request)

    # If the user is logged in and selected a valid language, update the
    # preferred_language field in the user model.
    logger.info("set_user_language called")

    if request.user.is_authenticated:
        lang_code = request.POST.get("language")
        if lang_code and lang_code in dict(settings.LANGUAGES):
            request.user.preferred_language = lang_code
            request.user.save(update_fields=["preferred_language"])
            activate(lang_code)
            logger.info("User %s set preferred_language to %s", request.user, lang_code)

    return response
