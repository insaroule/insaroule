from uuid import uuid4
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    REQUIRED_FIELDS = ["email", "email_verified"]

    uuid = models.UUIDField(
        _("UUID"),
        default=uuid4,
        unique=True,
        primary_key=True,
        editable=False,
    )

    email = models.EmailField(_("Email Address"), unique=True)
    email_verified = models.BooleanField(default=False)
