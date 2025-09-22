from django.conf import settings


def constants(request):
    return {
        "SUPPORT_EMAIL": settings.SUPPORT_EMAIL,
        "TERMS_OF_SERVICE": settings.TERMS_OF_SERVICE,
        "PRIVACY_POLICY": settings.PRIVACY_POLICY,
        "LEGAL_NOTICE": settings.LEGAL_NOTICE,
    }
